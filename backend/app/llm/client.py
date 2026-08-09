import time

from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    return _client


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.3,
    stream: bool = False,
    response_format: str | None = None,
) -> tuple:
    """调用 chat 模型，返回 (completion, latency_ms)。

    response_format: None 或 "json_object"。DeepSeek 的 json 模式要求 prompt 里出现 "json" 字样。
    """
    client = get_client()
    kwargs: dict = {
        "model": model or settings.deepseek_model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }
    if response_format == "json_object":
        kwargs["response_format"] = {"type": "json_object"}

    start = time.time()
    resp = client.chat.completions.create(**kwargs)
    latency_ms = int((time.time() - start) * 1000)
    return resp, latency_ms


def chat_json(messages: list[dict], *, temperature: float = 0.2) -> str:
    """要求模型只输出 JSON 字符串（配合 prompt 里的 schema 说明）。"""
    resp, _ = chat(messages, temperature=temperature, response_format="json_object")
    return resp.choices[0].message.content or ""


def stream_chat(messages: list[dict], *, model: str | None = None, temperature: float = 0.3):
    """流式调用 chat 模型，逐段 yield 文本增量（SSE 用）。"""
    client = get_client()
    stream = client.chat.completions.create(
        model=model or settings.deepseek_model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
