import json
from pathlib import Path
from typing import Callable

class Session:
    def __init__(self, system_prompt: str, path: Path | None = None):
        self.path = path
        self.messages = [{"role": "system", "content": system_prompt}]
        self.dirty = False

    def add(self, role: str, content: str, tool_calls=None, tool_call_id=None) -> None:
        msg = {"role": role, "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        self.messages.append(msg)
        self.dirty = True

    def to_messages(self) -> list[dict]:
        return list(self.messages)

    def save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                for m in self.messages:
                    f.write(json.dumps(m, ensure_ascii=False) + "\n")
            self.dirty = False

    @classmethod
    def load(cls, path: Path) -> "Session":
        s = cls("", path)
        s.messages = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    s.messages.append(json.loads(line))
        return s

    def _estimate(self) -> int:
        return len(json.dumps(self.messages, ensure_ascii=False)) // 4

    def maybe_compress(self, summarize: Callable[[str], str], max_tokens: int, ratio: float = 0.8) -> None:
        if self._estimate() <= ratio * max_tokens or len(self.messages) <= 8:
            return
        k = len(self.messages) - 6
        # 不能把保留窗口的起点切在孤儿 tool 消息上（其 assistant.tool_calls 被切走会导致 API 400）：
        # 回退 k 直到它不再指向 tool 消息，即落到所属 assistant 或普通消息上。
        while k > 0 and self.messages[k].get("role") == "tool":
            k -= 1
        if k <= 1:   # 回退过头，本轮没有可安全压缩的头部
            return
        base_system = self.messages[0]            # 原始 system（规则/skills/文件索引）必须保留
        head = self.messages[1:k]
        if not head:
            return
        summary = summarize(json.dumps(head, ensure_ascii=False))
        if not summary or not summary.strip():
            return   # 摘要失败：保留完整历史，下轮重试，绝不丢数据
        self.messages = [base_system,
                         {"role": "system", "content": f"[会话历史摘要] {summary}"}] + self.messages[k:]
        self.dirty = True
