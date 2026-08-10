"""SSE 流式接口冒烟测试：确认能收到 meta → 多段 delta → done。"""
import json
import os
import urllib.request

BASE = "http://localhost:8000"
OUT = os.path.join(os.path.dirname(__file__), "data", "sse_result.txt")
lines = []

req = urllib.request.Request(
    BASE + "/api/qa/stream",
    data=json.dumps({"query": "为什么 RAG 能减少幻觉？"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req)
print(f"Content-Type: {resp.headers.get('Content-Type')}")

meta = None
deltas = 0
done = False
buffer = b""
while True:
    chunk = resp.read(64)
    if not chunk:
        break
    buffer += chunk
    while b"\n\n" in buffer:
        frame, buffer = buffer.split(b"\n\n", 1)
        line = frame.strip()
        if line.startswith(b"data:"):
            ev = json.loads(line[5:].strip().decode("utf-8"))
            if ev["type"] == "meta":
                meta = ev
            elif ev["type"] == "delta":
                deltas += 1
            elif ev["type"] == "done":
                done = True

lines.append(f"Content-Type: {resp.headers.get('Content-Type')}")
lines.append(f"meta: sufficient={meta['sufficient']} sources={len(meta['sources'])} cached={meta['cached']}")
lines.append(f"delta 事件数: {deltas}")
lines.append(f"done: {done}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("done")
