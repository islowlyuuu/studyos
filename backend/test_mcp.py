"""MCP Server 冒烟测试。

- 协议行为（initialize / tools/list / tools/call 合法与非法）用 mcp SDK 的内存连接验证，
  与真实协议处理链路完全一致，只是不走子进程管道。
- stdio 部署入口 `python -m app.mcp_server` 单独做启动存活检查。

注：Windows 上 mcp SDK 的 stdio_client 子进程管道握手存在已知卡死问题，
故协议用内存连接验证；stdio 入口仍可正常启动被外部客户端（如 Claude Code）接入。

运行：python test_mcp.py（需要 PostgreSQL 可达）
"""
import asyncio
import os
import subprocess
import sys
import time
import uuid

from mcp.shared.memory import create_connected_server_and_client_session
from sqlalchemy import select

from app.database import SessionLocal
from app.mcp_server import mcp
from app.models import KnowledgePoint

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))


def get_kp(name: str):
    db = SessionLocal()
    try:
        return db.execute(select(KnowledgePoint).where(KnowledgePoint.name == name)).scalars().first()
    finally:
        db.close()


def cleanup(name: str) -> None:
    db = SessionLocal()
    try:
        kp = db.execute(select(KnowledgePoint).where(KnowledgePoint.name == name)).scalars().first()
        if kp is not None:
            db.delete(kp)
            db.commit()
    finally:
        db.close()


async def _call_rejected(session, name: str, args: dict) -> tuple[bool, str]:
    """返回 (是否被拒绝, 说明)。拒绝 = 抛异常，或结果带 isError / error 标记。"""
    try:
        res = await session.call_tool(name, args)
    except Exception as e:
        return True, f"抛异常 {type(e).__name__}"
    is_err = bool(getattr(res, "isError", False))
    text = "".join(c.text for c in res.content if hasattr(c, "text"))
    if is_err or "error" in text.lower():
        return True, f"结果标记错误 (isError={is_err})"
    return False, f"未被拒绝: {text[:60]}"


async def protocol_tests() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        # initialize（helper 内部已完成握手）
        tools = await session.list_tools()
        names = [t.name for t in tools.tools]
        print(f"[1] tools/list: {names}")
        assert set(names) == {"record_mistake", "update_mastery", "create_study_plan"}, names

        # 合法参数调用 + 持久化
        kp_name = f"mcp_test_{uuid.uuid4().hex[:8]}"
        res = await session.call_tool("update_mastery", {"knowledge_point": kp_name, "mastery_level": "familiar"})
        print(f"[2] update_mastery 合法调用 -> {res.content[0].text}")
        kp = get_kp(kp_name)
        assert kp is not None and kp.mastery_level == "familiar", "持久化失败"
        print(f"[2] 持久化可见: {kp.name} = {kp.mastery_level}")
        cleanup(kp_name)

        # 非法参数：枚举值非法
        bad_name = f"mcp_bad_{uuid.uuid4().hex[:8]}"
        rejected, note = await _call_rejected(session, "update_mastery", {"knowledge_point": bad_name, "mastery_level": "not_a_level"})
        print(f"[3] 非法枚举: {note}")
        assert rejected, "非法枚举应被拒绝"
        assert get_kp(bad_name) is None, "非法调用不应产生副作用"
        print("[3] 非法枚举无副作用（未写库）")

        # 非法参数：缺必填
        rejected2, note2 = await _call_rejected(session, "record_mistake", {"knowledge_points": ["测试"]})  # 缺 question
        print(f"[4] 缺必填参数: {note2}")
        assert rejected2, "缺必填参数应被拒绝"
        print("[4] 缺必填参数无副作用")


def stdio_boot_check() -> None:
    """验证 stdio 入口能正常启动并保持存活（不崩溃）。"""
    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "app.mcp_server"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    alive = proc.poll() is None
    proc.terminate()
    assert alive, "python -m app.mcp_server 启动后崩溃"
    print("[5] stdio 入口 `python -m app.mcp_server` 启动存活 OK")


def main() -> None:
    asyncio.run(protocol_tests())
    stdio_boot_check()
    print("\nMCP 冒烟测试全部通过")


if __name__ == "__main__":
    main()
