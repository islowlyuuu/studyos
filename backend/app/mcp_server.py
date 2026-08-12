"""MCP Server：把 StudyOS 的 Agent 工具暴露为标准 MCP 协议，复用 app/agent/tools 的参数模型与持久化逻辑。

启动：python -m app.mcp_server（stdio 传输）
客户端连接：任何支持 MCP 的客户端（如 Claude Code）以 stdio 子进程方式接入。
"""
from typing import Literal

from mcp.server.fastmcp import FastMCP

from app.agent.tools import (
    CreateStudyPlanArgs,
    RecordMistakeArgs,
    UpdateMasteryArgs,
    create_study_plan,
    record_mistake,
    update_mastery,
)

DEFAULT_USER_ID = 1

mcp = FastMCP("studyos")

# 与 app/agent/tools.TOOL_REGISTRY 保持一致的参数结构，保证 tools/list 与 Function Calling 路径同源
MasteryLevel = Literal["new", "learning", "familiar", "mastered", "needs_review"]


@mcp.tool(name="record_mistake", description="记录一道错题及其涉及的薄弱知识点，用于后续复习")
def _record_mistake(question: str, knowledge_points: list[str], note: str = "") -> str:
    return record_mistake(DEFAULT_USER_ID, RecordMistakeArgs(question=question, knowledge_points=knowledge_points, note=note))


@mcp.tool(name="update_mastery", description="更新某个知识点的掌握度（new/learning/familiar/mastered/needs_review）")
def _update_mastery(knowledge_point: str, mastery_level: MasteryLevel) -> str:
    return update_mastery(DEFAULT_USER_ID, UpdateMasteryArgs(knowledge_point=knowledge_point, mastery_level=mastery_level))


@mcp.tool(name="create_study_plan", description="根据学习目标生成一份每日学习计划")
def _create_study_plan(goal: str, focus_points: list[str] | None = None, duration_days: int = 7) -> str:
    return create_study_plan(
        DEFAULT_USER_ID,
        CreateStudyPlanArgs(goal=goal, focus_points=focus_points or [], duration_days=duration_days),
    )


if __name__ == "__main__":
    mcp.run()
