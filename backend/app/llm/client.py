import time

from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None


def _log_call(model: str, latency_ms: int, resp=None, streamed_tokens: int = 0) -> None:
    """记录一次模型调用（模型、token、延迟、估算成本）。"""
    from app.database import SessionLocal
    from app.models import LLMCallLog

    usage = getattr(resp, "usage", None) if resp is not None else None
    in_tok = usage.prompt_tokens if usage else 0
    out_tok = usage.completion_tokens if usage else streamed_tokens
    cost = (
        in_tok / 1e6 * settings.cost_per_1m_input
        + out_tok / 1e6 * settings.cost_per_1m_output
    )
    db = SessionLocal()
    try:
        db.add(
            LLMCallLog(
                model=model,
                prompt_version="v1",
                input_tokens=in_tok,
                output_tokens=out_tok,
                latency_ms=latency_ms,
                estimated_cost=cost,
            )
        )
        db.commit()
    finally:
        db.close()


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
    tools: list[dict] | None = None,
) -> tuple:
    """调用 chat 模型，返回 (completion, latency_ms)。

    response_format: None 或 "json_object"。DeepSeek 的 json 模式要求 prompt 里出现 "json" 字样。
    tools: OpenAI 格式的工具定义列表，用于 Function Calling。
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
    if tools:
        kwargs["tools"] = tools

    model = kwargs["model"]
    start = time.time()
    resp = client.chat.completions.create(**kwargs)
    latency_ms = int((time.time() - start) * 1000)
    _log_call(model, latency_ms, resp=resp)
    return resp, latency_ms


def chat_json(messages: list[dict], *, temperature: float = 0.2) -> str:
    """要求模型只输出 JSON 字符串（配合 prompt 里的 schema 说明）。"""
    resp, _ = chat(messages, temperature=temperature, response_format="json_object")
    return resp.choices[0].message.content or ""


def stream_chat(messages: list[dict], *, model: str | None = None, temperature: float = 0.3):
    """流式调用 chat 模型，逐段 yield 文本增量（SSE 用）。"""
    client = get_client()
    model = model or settings.deepseek_model
    start = time.time()
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    n = 0
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            n += 1
            yield chunk.choices[0].delta.content
    latency_ms = int((time.time() - start) * 1000)
    _log_call(model, latency_ms, streamed_tokens=n)
