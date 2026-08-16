import json
import time
from dataclasses import dataclass, field
import requests
from config import LLMConfig

class LLMError(Exception): pass
class LLMAuthError(LLMError): pass
class LLMRateLimitError(LLMError): pass

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class LLMResult:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)

class LLMClient:
    def __init__(self, config: LLMConfig, timeout: float = 60.0, max_retries: int = 3):
        self.config = config
        self.timeout = timeout
        self.max_retries = max_retries

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             model: str | None = None) -> LLMResult:
        payload = {"model": model or self.config.model, "messages": messages}
        if tools:
            payload["tools"] = tools
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        url = f"{self.config.base_url}/chat/completions"
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                if resp.status_code == 401:
                    raise LLMAuthError("401：API key 无效或余额不足")
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                calls = [ToolCall(tc["id"], tc["function"]["name"],
                                  json.loads(tc["function"].get("arguments") or "{}"))
                         for tc in msg.get("tool_calls", [])]
                return LLMResult(msg.get("content"), calls)
            except requests.exceptions.HTTPError as e:
                code = getattr(getattr(e, "response", None), "status_code", None)
                if code == 401:
                    raise LLMAuthError("401：API key 无效或余额不足") from e
                if code == 429 or (code and code >= 500):
                    last_exc = e
                    time.sleep(2 ** attempt)
                    continue
                raise
            except requests.exceptions.SSLError:
                # a-Shell 直连时 SSL 证书链可能缺失，回退到 certifi
                # 注意：SSLError 是 ConnectionError 的子类，此分支必须排在网络重试分支之前
                import certifi
                resp = requests.post(url, headers=headers, json=payload,
                                     timeout=self.timeout, verify=certifi.where())
                if resp.status_code == 401:
                    raise LLMAuthError("401：API key 无效或余额不足")
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                calls = [ToolCall(tc["id"], tc["function"]["name"],
                                  json.loads(tc["function"].get("arguments") or "{}"))
                         for tc in msg.get("tool_calls", [])]
                return LLMResult(msg.get("content"), calls)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # iPad 蜂窝网络下最常见的失败：超时/连接中断，指数退避重试
                last_exc = e
                time.sleep(2 ** attempt)
                continue
        raise LLMRateLimitError(f"重试耗尽：{last_exc}")
