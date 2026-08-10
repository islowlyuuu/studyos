import re
import subprocess

from pydantic_settings import BaseSettings, SettingsConfigDict


def _wsl_ip() -> str | None:
    """WSL2 里跑着 postgres/redis，本机 localhost 转发不可靠，动态探测 VM 的 IP。"""
    try:
        result = subprocess.run(
            ["wsl", "bash", "-lc", "hostname -I"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        parts = result.stdout.strip().split()
        return parts[0] if parts else None
    except Exception:
        return None


def _swap_host(url: str, host: str) -> str:
    return re.sub(r"@(localhost|127\.0\.0\.1):", f"@{host}:", url)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "StudyOS"

    database_url: str = "postgresql+psycopg://studyos:studyos@localhost:5432/studyos"
    redis_url: str = "redis://localhost:6379/0"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512

    vector_top_k: int = 8
    min_similarity: float = 0.4  # 低于此相似度视为证据不足
    cache_ttl_seconds: int = 3600
    score_threshold: float = 0.6  # 批改低于此分视为未通过，标记薄弱

    # 成本估算（元 / 百万 token），按 DeepSeek 约价
    cost_per_1m_input: float = 2.0
    cost_per_1m_output: float = 8.0

    eval_top_k: int = 8  # 评测用检索深度

    max_agent_steps: int = 8
    agent_timeout_seconds: int = 60


settings = Settings()

_host = _wsl_ip()
if _host:
    settings.database_url = _swap_host(settings.database_url, _host)
    settings.redis_url = _swap_host(settings.redis_url, _host)
