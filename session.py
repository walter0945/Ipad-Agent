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
        head = self.messages[:len(self.messages) - 6]
        summary = summarize(json.dumps(head, ensure_ascii=False))
        self.messages = [{"role": "system", "content": f"[会话历史摘要] {summary}"}] + self.messages[len(self.messages) - 6:]
        self.dirty = True
