"""端到端闭环冒烟测试：问答(含缓存) → 出题 → 批改。

输出写到 data/e2e_result.txt（UTF-8），避免控制台编码问题。
"""
import json
import urllib.request

BASE = "http://localhost:8000"
OUT = __import__("os").path.join(__import__("os").path.dirname(__file__), "data", "e2e_result.txt")
lines = []


def post(path: str, data: dict):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())


def main() -> None:
    # 1. 非流式问答
    r1 = post("/api/qa/ask", {"query": "什么是 RAG？它的流程是什么？"})
    lines.append(f"[1] QA 非流式: cached={r1.get('cached')} sufficient={r1['sufficient']} latency={r1['latency_ms']}ms")
    lines.append(f"    sources={len(r1['sources'])} 个, answer前80字: {r1['answer'][:80]}...")

    # 2. 相同问题再问 → 命中缓存
    r2 = post("/api/qa/ask", {"query": "什么是 RAG？它的流程是什么？"})
    lines.append(f"[2] QA 第二次(应命中缓存): cached={r2.get('cached')}")

    # 3. 出题
    g = post("/api/practice/generate", {"topic": "RAG 检索增强生成"})
    lines.append(f"[3] 出题: id={g.get('id')} type={g.get('question_type')} kps={g.get('knowledge_points')}")
    lines.append(f"    题目: {str(g.get('content'))[:80]}...")

    # 4. 答题批改
    a = post("/api/practice/answer", {"question_id": g["id"], "answer": "RAG 是检索增强生成，先检索知识库相关片段，再让模型只依据片段生成带引用的回答。"})
    lines.append(f"[4] 批改: score={a.get('score')} passed={a.get('passed')} 薄弱点={a.get('mistakes')}")
    lines.append(f"    feedback: {str(a.get('feedback'))[:80]}...")

    # 5. Agent 工具调用（记录错题 + 更新掌握度）
    agent = post("/api/agent/run", {"message": "我答错了一道关于向量的题，帮我记录错题，知识点是向量和余弦相似度"})
    lines.append(f"[5] Agent: status={agent.get('status')} steps={agent.get('steps')}")
    for t in agent.get("trace", []):
        lines.append(f"    step{t['step']}: tool={t.get('tool')} ok={t.get('ok')}")

    # 6. 状态可见
    kps = json.loads(urllib.request.urlopen(BASE + "/api/agent/knowledge-points").read())
    lines.append(f"[6] 知识点状态: {[(k['name'], k['mastery_level']) for k in kps]}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("done")


if __name__ == "__main__":
    main()
