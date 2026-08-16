import os
from dataclasses import dataclass
from typing import Mapping

class ConfigError(Exception):
    pass

@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str
    api_key: str
    model: str

PROVIDER_PRESETS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    "grok": {"base_url": "https://api.x.ai/v1", "model": "grok-4"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-5-codex"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "model": "anthropic/claude-sonnet-4-5"},
    "anthropic": {"base_url": "https://api.anthropic.com", "model": "claude-sonnet-4-5"},
}

def load_llm_config(env: Mapping | None = None) -> LLMConfig:
    if env is None:
        env = os.environ
    provider = (env.get("PROVIDER") or "deepseek").strip().lower()
    preset = PROVIDER_PRESETS.get(provider)
    if preset is None and not env.get("LLM_BASE_URL"):
        raise ConfigError(f"未知 provider: {provider}，且未提供 LLM_BASE_URL")
    base_url = (env.get("LLM_BASE_URL") or (preset["base_url"] if preset else "")).rstrip("/")
    model = env.get("LLM_MODEL") or (preset["model"] if preset else "")
    api_key = env.get("LLM_API_KEY", "")
    if not api_key:
        raise ConfigError("缺少 LLM_API_KEY")
    return LLMConfig(provider=provider, base_url=base_url, api_key=api_key, model=model)
