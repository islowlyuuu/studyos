import json

from app.llm.client import chat, chat_json

# 基础对话测试
resp, latency = chat([{"role": "user", "content": "用一句话说明什么是 RAG"}])
print("回答:", resp.choices[0].message.content)
print("模型:", resp.model)
print("tokens:", resp.usage)
print("latency_ms:", latency)

# 结构化输出测试
schema_hint = "返回 JSON，字段：name(字符串), difficulty(数字1-5), reason(字符串)"
resp_json, latency2 = chat(
    [{"role": "user", "content": f"出一道关于 Attention 的题，{schema_hint}"}],
    response_format="json_object",
)
parsed = json.loads(resp_json.choices[0].message.content)
print("\n结构化输出:", parsed)
print("latency_ms:", latency2)
