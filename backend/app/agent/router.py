"""意图路由循环：把用户消息交给模型，模型决定调用工具或直接回答，循环直到结束。"""
import json
import time

from app.agent.tools import execute_tool, tools_spec
from app.config import settings
from app.database import SessionLocal
from app.llm.client import chat
from app.models import AgentRun

SYSTEM_PROMPT = (
    "你是个人学习助手。根据用户意图选择合适的工具执行："
    "记录错题、更新知识点掌握度、生成学习计划。"
    "需要工具时调用工具；不需要时直接回答。"
)


def run_agent(message: str, user_id: int) -> dict:
    max_steps = settings.max_agent_steps
    timeout = settings.agent_timeout_seconds
    start = time.time()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]
    trace: list[dict] = []
    steps = 0
    answer = ""
    status = "done"

    while steps < max_steps:
        if time.time() - start > timeout:
            status = "timeout"
            break
        steps += 1

        resp, _ = chat(messages, tools=tools_spec(), temperature=0.2)
        msg = resp.choices[0].message

        if not getattr(msg, "tool_calls", None):
            answer = msg.content or ""
            break

        for tc in msg.tool_calls:
            fn = tc.function
            try:
                args = json.loads(fn.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            trace.append({"step": steps, "tool": fn.name, "args": args})
            ok, output = execute_tool(fn.name, args, user_id)
            trace[-1]["ok"] = ok
            trace[-1]["output"] = output
            messages.append(
                {"role": "assistant", "content": None, "tool_calls": [tc]}
            )
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": json.dumps({"ok": ok, "output": output}, ensure_ascii=False)}
            )
    else:
        # while 正常走完未 break = 达到最大步数
        status = "max_steps"

    if status == "timeout":
        answer = "已达超时限制，返回当前中间结果。"
    elif status == "max_steps":
        answer = "已达最大工具调用步数，返回当前中间结果。"

    _persist_run(user_id, status, trace, resp if "resp" in locals() else None)
    return {"status": status, "steps": steps, "trace": trace, "answer": answer}


def _persist_run(user_id: int, status: str, trace: list[dict], resp) -> None:
    tokens = None
    if resp is not None and getattr(resp, "usage", None) is not None:
        tokens = {"input": resp.usage.prompt_tokens, "output": resp.usage.completion_tokens}
    db = SessionLocal()
    try:
        run = AgentRun(
            user_id=user_id,
            intent="agent_chat",
            model=settings.deepseek_model,
            prompt_version="v1",
            input_tokens=(tokens or {}).get("input", 0),
            output_tokens=(tokens or {}).get("output", 0),
            tool_trace=trace,
            status=status,
        )
        db.add(run)
        db.commit()
    finally:
        db.close()
