# iPad 本地 AI Agent 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可在 Windows 本机运行、并可拷入 iPad a-Shell 的纯 Python 本地 AI agent（DeepSeek/Qwen 等 provider + 文件/表格/搜索工具 + skill + 权限门控 + 会话持久化）。

**Architecture:** 分层结构——`llm.py`（Provider 抽象客户端）→ `tools/`（意图注册表，工具闭包内嵌 PermissionGate）→ `agent.py`（编排循环：组装 system prompt → 调 LLM → 门控执行工具 → 回填）。TDD 全流程，pytest 在 Windows 本机跑。

**Tech Stack:** Python 3.12、`requests`、`openpyxl`、`rich`、`python-dotenv`、`pytest`。

## Global Constraints

- Python 3.12+；依赖仅限 `requests openpyxl rich python-dotenv`（运行）+ `pytest`（测试）；**不使用 LangChain/LangGraph**。
- API key 只从环境变量/`.env` 读取，绝不硬编码；`.env` 进 `.gitignore`。
- 所有文件操作限制在 `sandbox_root`（默认项目下 `workspace/`）内，密钥文件（`.env`/`.pem`/`.key`）不可读。
- 工具协议统一 OpenAI function-calling JSON（`{"type":"function","function":{"name","description","parameters"}}`）。
- 每个任务以"写失败测试 → 跑失败 → 最小实现 → 跑绿 → commit"为节奏；测试文件放 `tests/`，用 `unittest`（零额外依赖）而非 pytest 插件特性。

---

### Task 1: 项目骨架 + config.py（Provider 预设）

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `LLMConfig(provider: str, base_url: str, api_key: str, model: str)`（frozen dataclass）
  - `PROVIDER_PRESETS: dict[str, dict[str, str]]`
  - `load_llm_config(env: Mapping | None = None) -> LLMConfig`
  - `ConfigError(Exception)`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config.py
import unittest
from config import load_llm_config, LLMConfig, ConfigError

class TestLoadLLMConfig(unittest.TestCase):
    def test_deepseek_preset(self):
        c = load_llm_config({"LLM_API_KEY": "sk-1"})
        self.assertEqual(c, LLMConfig("deepseek", "https://api.deepseek.com", "sk-1", "deepseek-chat"))

    def test_qwen_preset(self):
        c = load_llm_config({"LLM_API_KEY": "sk-2", "PROVIDER": "qwen"})
        self.assertEqual(c.base_url, "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(c.model, "qwen-plus")

    def test_override(self):
        c = load_llm_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "http://localhost:11434/v1", "LLM_MODEL": "llama3"})
        self.assertEqual(c.base_url, "http://localhost:11434/v1")
        self.assertEqual(c.model, "llama3")

    def test_missing_key_raises(self):
        with self.assertRaises(ConfigError):
            load_llm_config({})

    def test_unknown_provider_without_override_raises(self):
        with self.assertRaises(ConfigError):
            load_llm_config({"LLM_API_KEY": "k", "PROVIDER": "nope"})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_config -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'config'`）

- [ ] **Step 3: 写 config.py**

```python
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
```

- [ ] **Step 4: 写骨架文件**

```text
# requirements.txt
requests
openpyxl
rich
python-dotenv

# .env.example
PROVIDER=deepseek
LLM_BASE_URL=
LLM_API_KEY=sk-your-key-here
LLM_MODEL=

# .gitignore
.venv/
.env
__pycache__/
workspace/
*.pyc
```

- [ ] **Step 5: 跑测试确认通过**

Run: `python -m unittest tests.test_config -v`
Expected: PASS（5 passed）

- [ ] **Step 6: commit**

```bash
git add requirements.txt .env.example .gitignore config.py tests/test_config.py
git commit -m "feat: project scaffold and provider-preset config"
```

---

### Task 2: llm.py（Provider 抽象客户端）

**Files:**
- Create: `llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: `LLMConfig`（Task 1）
- Produces:
  - `ToolCall(id: str, name: str, arguments: dict)`
  - `LLMResult(content: str | None, tool_calls: list[ToolCall])`
  - `LLMError(Exception)` / `LLMAuthError(LLMError)` / `LLMRateLimitError(LLMError)`
  - `LLMClient(config, timeout=60.0, max_retries=3)`
  - `LLMClient.chat(messages: list[dict], tools: list[dict] | None = None) -> LLMResult`

- [ ] **Step 1: 写失败测试（用 unittest.mock 打桩 requests）**

```python
# tests/test_llm.py
import json, unittest
from unittest.mock import patch, MagicMock
import requests
from config import LLMConfig
from llm import LLMClient, LLMResult, ToolCall, LLMAuthError, LLMRateLimitError

CFG = LLMConfig("deepseek", "https://api.deepseek.com", "sk-1", "deepseek-chat")

class TestChat(unittest.TestCase):
    def _resp(self, payload):
        m = MagicMock(); m.raise_for_status.return_value = None; m.json.return_value = payload
        return m

    def test_content_only(self):
        with patch("llm.requests.post") as post:
            post.return_value = self._resp({"choices": [{"message": {"content": "你好"}}]})
            r = LLMClient(CFG).chat([{"role": "user", "content": "hi"}])
        self.assertEqual(r, LLMResult("你好", []))
        _, kwargs = post.call_args
        self.assertEqual(kwargs["json"]["model"], "deepseek-chat")

    def test_tool_calls(self):
        body = {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "t1", "function": {"name": "read_file", "arguments": '{"path": "a.txt"}'}}]}}]}
        with patch("llm.requests.post") as post:
            post.return_value = self._resp(body)
            r = LLMClient(CFG).chat([{"role": "user", "content": "读a.txt"}], tools=[{}])
        self.assertEqual(r.tool_calls, [ToolCall("t1", "read_file", {"path": "a.txt"})])

    def test_401_raises_auth(self):
        err = requests.HTTPError(); err.response = MagicMock(status_code=401)
        with patch("llm.requests.post") as post:
            post.side_effect = err
            with self.assertRaises(LLMAuthError):
                LLMClient(CFG).chat([{"role": "user", "content": "x"}])

    def test_429_retries_then_succeeds(self):
        err = requests.HTTPError(); err.response = MagicMock(status_code=429)
        ok = self._resp({"choices": [{"message": {"content": "ok"}}]})
        with patch("llm.requests.post") as post:
            post.side_effect = [err, ok]
            with patch("llm.time.sleep") as sleep:
                r = LLMClient(CFG).chat([{"role": "user", "content": "x"}])
        self.assertEqual(r.content, "ok")
        self.assertTrue(sleep.called)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_llm -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'llm'`）

- [ ] **Step 3: 写 llm.py**

```python
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

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResult:
        payload = {"model": self.config.model, "messages": messages}
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
                import certifi
                resp = requests.post(url, headers=headers, json=payload,
                                     timeout=self.timeout, verify=certifi.where())
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                calls = [ToolCall(tc["id"], tc["function"]["name"],
                                  json.loads(tc["function"].get("arguments") or "{}"))
                         for tc in msg.get("tool_calls", [])]
                return LLMResult(msg.get("content"), calls)
        raise LLMRateLimitError("重试耗尽：持续 429/5xx")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_llm -v`
Expected: PASS（4 passed）

- [ ] **Step 5: commit**

```bash
git add llm.py tests/test_llm.py
git commit -m "feat: provider-abstract LLM client with retry/auth/ssl handling"
```

---

### Task 3: permissions.py（分级权限门控）

**Files:**
- Create: `permissions.py`
- Test: `tests/test_permissions.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `PermissionGate(sandbox_root: Path, shell_allowlist: tuple[str, ...], confirm: Callable[[str], bool], strong_confirm: Callable[[str], bool])`
  - `PermissionGate.is_within_root(path: Path) -> bool`
  - `PermissionGate.read(path) -> bool` / `write(path) -> bool` / `delete(path) -> bool` / `shell(command) -> bool`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_permissions.py
import unittest
from pathlib import Path
from permissions import PermissionGate

class TestGate(unittest.TestCase):
    def _gate(self, confirm=lambda m: True, strong=lambda m: True):
        return PermissionGate(Path("workspace"), ("ls", "python3"), confirm, strong)

    def test_read_within_root_no_confirm(self):
        g = self._gate(confirm=lambda m: (_ for _ in ()).throw(AssertionError()))
        self.assertTrue(g.read(Path("workspace/a.txt")))

    def test_read_outside_root_denied(self):
        g = self._gate()
        self.assertFalse(g.read(Path("C:/etc/passwd")))

    def test_write_requires_confirm(self):
        called = []
        g = self._gate(confirm=lambda m: called.append(m) or True)
        self.assertTrue(g.write(Path("workspace/b.txt")))
        self.assertTrue(called)

    def test_delete_requires_strong_confirm(self):
        seen = {}
        g = self._gate(strong=lambda m: seen.setdefault("strong", True) and False)
        self.assertFalse(g.delete(Path("workspace/b.txt")))
        self.assertIn("strong", seen)

    def test_shell_allowlist_and_confirm(self):
        g = self._gate()
        self.assertTrue(g.shell("ls -l"))
        self.assertFalse(g.shell("rm -rf /"))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_permissions -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 写 permissions.py**

```python
from pathlib import Path
from typing import Callable

class PermissionGate:
    def __init__(self, sandbox_root: Path, shell_allowlist: tuple[str, ...],
                 confirm: Callable[[str], bool], strong_confirm: Callable[[str], bool]):
        self.sandbox_root = sandbox_root.resolve()
        self.shell_allowlist = shell_allowlist
        self.confirm = confirm
        self.strong_confirm = strong_confirm

    def is_within_root(self, path: Path) -> bool:
        try:
            self.sandbox_root.joinpath(path).resolve().relative_to(self.sandbox_root)
            return True
        except ValueError:
            return False

    def read(self, path: Path) -> bool:
        return self.is_within_root(path)

    def write(self, path: Path) -> bool:
        return self.is_within_root(path) and self.confirm(f"确认写入 {path}？")

    def delete(self, path: Path) -> bool:
        return self.is_within_root(path) and self.strong_confirm(f"⚠️ 确认删除 {path}？此操作不可撤销")

    def shell(self, command: str) -> bool:
        head = command.strip().split(" ", 1)[0]
        if head not in self.shell_allowlist:
            return False
        return self.confirm(f"确认执行命令：{command}？")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_permissions -v`
Expected: PASS（5 passed）

- [ ] **Step 5: commit**

```bash
git add permissions.py tests/test_permissions.py
git commit -m "feat: graded permission gate (read/write/delete/shell)"
```

---

### Task 4: session.py（会话持久化 + 压缩）

**Files:**
- Create: `session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `Session(system_prompt: str, path: Path | None = None)`
  - `Session.add(role: str, content: str) -> None`
  - `Session.to_messages() -> list[dict]`
  - `Session.save() -> None` / `Session.load(path) -> Session`（classmethod）
  - `Session.maybe_compress(summarize: Callable[[str], str], max_tokens: int, ratio: float = 0.8) -> None`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_session.py
import json, unittest, tempfile
from pathlib import Path
from session import Session

class TestSession(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.jsonl"
            s = Session("sys", p); s.add("user", "hi"); s.add("assistant", "yo"); s.save()
            s2 = Session.load(p)
            self.assertEqual(s2.to_messages(), [{"role": "system", "content": "sys"},
                                                {"role": "user", "content": "hi"},
                                                {"role": "assistant", "content": "yo"}])

    def test_compress_keeps_recent(self):
        s = Session("sys")
        for i in range(20):
            s.add("user", f"msg-{i}")
        s.maybe_compress(lambda text: "摘要", max_tokens=50)
        self.assertTrue(any(m["role"] == "system" and "摘要" in m["content"] for m in s.to_messages()))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_session -v`
Expected: FAIL

- [ ] **Step 3: 写 session.py**

```python
import json
from pathlib import Path
from typing import Callable

class Session:
    def __init__(self, system_prompt: str, path: Path | None = None):
        self.path = path
        self.messages = [{"role": "system", "content": system_prompt}]
        self.dirty = False

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_session -v`
Expected: PASS（2 passed）

- [ ] **Step 5: commit**

```bash
git add session.py tests/test_session.py
git commit -m "feat: session persistence and context compression"
```

---

### Task 5: tools/__init__.py（工具注册表）

**Files:**
- Create: `tools/__init__.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `Tool(name: str, description: str, parameters: dict, func: Callable[[dict], str])`
  - `Registry().register(tool) -> None` / `.schemas() -> list[dict]` / `.run(name, arguments) -> str`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_registry.py
import unittest
from tools import Registry, Tool

class TestRegistry(unittest.TestCase):
    def test_register_and_run(self):
        r = Registry()
        r.register(Tool("echo", "repeat", {"type": "object", "properties": {"x": {"type": "string"}}},
                        lambda args: args["x"]))
        self.assertEqual(r.run("echo", {"x": "hi"}), "hi")
        self.assertEqual(len(r.schemas()), 1)

    def test_run_unknown_raises(self):
        with self.assertRaises(KeyError):
            Registry().run("nope", {})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_registry -v`
Expected: FAIL

- [ ] **Step 3: 写 tools/__init__.py**

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable[[dict], str]

class Registry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def schemas(self) -> list[dict]:
        return [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                  "parameters": t.parameters}}
                for t in self._tools.values()]

    def run(self, name: str, arguments: dict) -> str:
        if name not in self._tools:
            raise KeyError(f"未知工具: {name}")
        return self._tools[name].func(arguments)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_registry -v`
Expected: PASS（2 passed）

- [ ] **Step 5: commit**

```bash
git add tools/__init__.py tests/test_registry.py
git commit -m "feat: tool registry with schema generation"
```

---

### Task 6: tools/files.py（文件工具）

**Files:**
- Create: `tools/files.py`
- Test: `tests/test_files_tools.py`

**Interfaces:**
- Consumes: `Tool`、`Registry`（Task 5）、`PermissionGate`（Task 3）
- Produces: `make_files_tools(gate: PermissionGate) -> list[Tool]`，注册 `read_file`/`write_file`/`edit_file`/`list_dir`/`grep`/`glob`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_files_tools.py
import tempfile, unittest
from pathlib import Path
from permissions import PermissionGate
from tools.files import make_files_tools

def _tools(root: Path):
    gate = PermissionGate(root, (), lambda m: True, lambda m: True)
    return {t.name: t for t in make_files_tools(gate)}

class TestFileTools(unittest.TestCase):
    def test_read_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            t = _tools(root)
            t["write_file"].func({"path": "a.txt", "content": "hello"})
            self.assertIn("hello", t["read_file"].func({"path": "a.txt"}))

    def test_edit_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            t = _tools(root)
            t["write_file"].func({"path": "a.txt", "content": "foo bar"})
            t["edit_file"].func({"path": "a.txt", "old": "foo", "new": "baz"})
            self.assertIn("baz bar", t["read_file"].func({"path": "a.txt"}))

    def test_outside_root_denied(self):
        with tempfile.TemporaryDirectory() as d:
            t = _tools(Path(d))
            out = t["read_file"].func({"path": "../secret.txt"})
            self.assertIn("拒绝", out)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_files_tools -v`
Expected: FAIL

- [ ] **Step 3: 写 tools/files.py**

```python
import re
from pathlib import Path
from tools import Tool

def _resolve(gate, p: str) -> Path:
    return gate.sandbox_root.joinpath(p).resolve()

def make_files_tools(gate) -> list[Tool]:
    def read_file(args):
        p = _resolve(gate, args["path"])
        if not gate.read(p):
            return "拒绝：路径越界"
        start = args.get("start", 1); end = args.get("end")
        lines = p.read_text(encoding="utf-8").splitlines()
        seg = lines[start - 1:end] if end else lines[start - 1:]
        return "\n".join(seg)

    def write_file(args):
        p = _resolve(gate, args["path"])
        if not gate.write(p):
            return "拒绝：未确认写入或路径越界"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"], encoding="utf-8")
        return f"已写入 {p.name}"

    def edit_file(args):
        p = _resolve(gate, args["path"])
        if not gate.write(p):
            return "拒绝"
        text = p.read_text(encoding="utf-8")
        if args["old"] not in text:
            return "未找到要替换的文本"
        p.write_text(text.replace(args["old"], args["new"], 1), encoding="utf-8")
        return "已替换"

    def list_dir(args):
        p = _resolve(gate, args.get("path", "."))
        if not gate.read(p):
            return "拒绝"
        return "\n".join(sorted(str(x.relative_to(gate.sandbox_root)) for x in p.iterdir()))

    def grep(args):
        p = _resolve(gate, args.get("path", "."))
        if not gate.read(p):
            return "拒绝"
        pat = re.compile(args["pattern"])
        hits = []
        for f in p.rglob("*") if p.is_dir() else [p]:
            if f.is_file():
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if pat.search(line):
                        hits.append(f"{f.name}:{i}: {line.strip()}")
        return "\n".join(hits[:50])

    def glob(args):
        p = _resolve(gate, ".")
        matches = sorted(str(x.relative_to(p)) for x in p.glob(args["pattern"]))
        return "\n".join(matches[:100])

    return [
        Tool("read_file", "读文件（支持 start/end 行区间）",
             {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}}, "required": ["path"]}, read_file),
        Tool("write_file", "创建或覆盖文件",
             {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, write_file),
        Tool("edit_file", "精确查找替换",
             {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]}, edit_file),
        Tool("list_dir", "列出目录", {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}, list_dir),
        Tool("grep", "正则搜索文件内容", {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}, grep),
        Tool("glob", "按模式找文件", {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}, glob),
    ]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_files_tools -v`
Expected: PASS（3 passed）

- [ ] **Step 5: commit**

```bash
git add tools/files.py tests/test_files_tools.py
git commit -m "feat: file tools with sandbox containment"
```

---

### Task 7: tools/spreadsheet.py（表格工具）

**Files:**
- Create: `tools/spreadsheet.py`
- Test: `tests/test_spreadsheet_tools.py`

**Interfaces:**
- Consumes: `Tool`、`PermissionGate`
- Produces: `make_spreadsheet_tools(gate) -> list[Tool]`，注册 `sheet_list`/`sheet_read`/`sheet_write_cell`/`sheet_add_row`/`sheet_summary`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_spreadsheet_tools.py
import tempfile, unittest
from pathlib import Path
from permissions import PermissionGate
from tools.spreadsheet import make_spreadsheet_tools

def _tools(root: Path):
    gate = PermissionGate(root, (), lambda m: True, lambda m: True)
    return {t.name: t for t in make_spreadsheet_tools(gate)}

class TestSheetTools(unittest.TestCase):
    def test_write_read_cell(self):
        with tempfile.TemporaryDirectory() as d:
            t = _tools(Path(d))
            t["sheet_write_cell"].func({"path": "book.xlsx", "sheet": "Sheet1", "cell": "A1", "value": "42"})
            out = t["sheet_read"].func({"path": "book.xlsx", "sheet": "Sheet1"})
            self.assertIn("42", out)

    def test_summary(self):
        with tempfile.TemporaryDirectory() as d:
            t = _tools(Path(d))
            t["sheet_write_cell"].func({"path": "book.xlsx", "sheet": "Sheet1", "cell": "A1", "value": "name"})
            out = t["sheet_summary"].func({"path": "book.xlsx"})
            self.assertIn("Sheet1", out)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_spreadsheet_tools -v`
Expected: FAIL

- [ ] **Step 3: 写 tools/spreadsheet.py**

```python
import csv
from pathlib import Path
from tools import Tool
from openpyxl import load_workbook, Workbook

def _resolve(gate, p): return gate.sandbox_root.joinpath(p).resolve()

def make_spreadsheet_tools(gate) -> list[Tool]:
    def sheet_list(args):
        root = _resolve(gate, ".")
        files = [str(x.relative_to(gate.sandbox_root)) for x in root.glob("*")
                 if x.suffix.lower() in (".xlsx", ".csv")]
        return "\n".join(sorted(files)) or "（无表格文件）"

    def _read_xlsx(path, sheet=None):
        wb = load_workbook(path, data_only=True)
        ws = wb[sheet] if sheet else wb.active
        return "\n".join("\t".join("" if c is None else str(c) for c in row) for row in ws.iter_rows(values_only=True))

    def _read_csv(path):
        with open(path, newline="", encoding="utf-8-sig") as f:
            return "\n".join("\t".join(r) for r in csv.reader(f))

    def sheet_read(args):
        p = _resolve(gate, args["path"])
        if not gate.read(p): return "拒绝"
        return _read_xlsx(p, args.get("sheet")) if p.suffix.lower() == ".xlsx" else _read_csv(p)

    def sheet_write_cell(args):
        p = _resolve(gate, args["path"])
        if not gate.write(p): return "拒绝"
        if not p.exists():
            Workbook().save(p)
        wb = load_workbook(p)
        ws = wb[args.get("sheet", wb.sheetnames[0])] if args.get("sheet") in wb.sheetnames else wb.create_sheet(args.get("sheet", "Sheet1"))
        ws[args["cell"]] = args["value"]
        wb.save(p)
        return f"已写入 {p.name} {args.get('sheet','Sheet1')}!{args['cell']}"

    def sheet_add_row(args):
        p = _resolve(gate, args["path"])
        if not gate.write(p): return "拒绝"
        wb = load_workbook(p) if p.exists() else Workbook()
        ws = wb[args.get("sheet", wb.sheetnames[0])] if args.get("sheet") in wb.sheetnames else wb.create_sheet(args.get("sheet", "Sheet1"))
        ws.append(args["row"])
        wb.save(p)
        return f"已追加 {len(args['row'])} 列到 {p.name}"

    def sheet_summary(args):
        p = _resolve(gate, args["path"])
        if not gate.read(p): return "拒绝"
        wb = load_workbook(p, read_only=True)
        lines = [f"工作表: {', '.join(wb.sheetnames)}"]
        for name in wb.sheetnames:
            ws = wb[name]
            lines.append(f"- {name}: {ws.max_row} 行 x {ws.max_column} 列")
        wb.close()
        return "\n".join(lines)

    return [
        Tool("sheet_list", "列出工作目录下的 xlsx/csv 表格",
             {"type": "object", "properties": {}, "required": []}, sheet_list),
        Tool("sheet_read", "读表格内容（制表符分隔）",
             {"type": "object", "properties": {"path": {"type": "string"}, "sheet": {"type": "string"}}, "required": ["path"]}, sheet_read),
        Tool("sheet_write_cell", "写单元格",
             {"type": "object", "properties": {"path": {"type": "string"}, "sheet": {"type": "string"}, "cell": {"type": "string"}, "value": {"type": "string"}}, "required": ["path", "cell", "value"]}, sheet_write_cell),
        Tool("sheet_add_row", "追加一行",
             {"type": "object", "properties": {"path": {"type": "string"}, "sheet": {"type": "string"}, "row": {"type": "array", "items": {"type": "string"}}}, "required": ["path", "row"]}, sheet_add_row),
        Tool("sheet_summary", "表格结构概览（行数/列数/工作表）",
             {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, sheet_summary),
    ]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_spreadsheet_tools -v`
Expected: PASS（2 passed）

- [ ] **Step 5: commit**

```bash
git add tools/spreadsheet.py tests/test_spreadsheet_tools.py
git commit -m "feat: spreadsheet tools via openpyxl"
```

---

### Task 8: tools/shell.py（安全 Shell 工具）

**Files:**
- Create: `tools/shell.py`
- Test: `tests/test_shell_tools.py`

**Interfaces:**
- Consumes: `Tool`、`PermissionGate`
- Produces: `make_shell_tools(gate) -> list[Tool]`，注册 `run_shell`（拆 `&&`/`||`/`;`，拦 `|`/`$()`/反引号/`&`）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_shell_tools.py
import unittest
from pathlib import Path
from permissions import PermissionGate
from tools.shell import make_shell_tools, split_commands

class TestShell(unittest.TestCase):
    def test_split_commands(self):
        self.assertEqual(split_commands("echo a && echo b"), ["echo a", "echo b"])

    def test_block_pipe(self):
        gate = PermissionGate(Path("workspace"), ("echo",), lambda m: True, lambda m: True)
        tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
        self.assertIn("拒绝", tool.func({"command": "echo a | grep b"}))

    def test_run_allowed(self):
        gate = PermissionGate(Path("workspace"), ("echo",), lambda m: True, lambda m: True)
        tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
        self.assertIn("hi", tool.func({"command": "echo hi"}))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_shell_tools -v`
Expected: FAIL

- [ ] **Step 3: 写 tools/shell.py**

```python
import re
import subprocess
from tools import Tool

BLOCKED = re.compile(r"[|`&]|\$\(")

def split_commands(command: str) -> list[str]:
    return [c.strip() for c in re.split(r"&&|\|\||;", command) if c.strip()]

def make_shell_tools(gate) -> list[Tool]:
    def run_shell(args):
        command = args["command"]
        if BLOCKED.search(command):
            return "拒绝：命令含被拦截的语法（管道/&/命令替换）"
        outputs = []
        for cmd in split_commands(command):
            if not gate.shell(cmd):
                return f"拒绝：命令不在白名单或未确认 ({cmd})"
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               cwd=gate.sandbox_root, timeout=30)
            outputs.append((r.stdout or "") + (r.stderr or ""))
        return "\n".join(outputs).strip() or "（无输出）"
    return [Tool("run_shell", "执行 shell 命令（白名单 + 确认）",
                 {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}, run_shell)]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_shell_tools -v`
Expected: PASS（3 passed）

- [ ] **Step 5: commit**

```bash
git add tools/shell.py tests/test_shell_tools.py
git commit -m "feat: guarded shell tool with pipe blocking"
```

---

### Task 9: tools/search.py（搜索工具）

**Files:**
- Create: `tools/search.py`
- Test: `tests/test_search_tools.py`

**Interfaces:**
- Consumes: `Tool`
- Produces: `make_search_tools() -> list[Tool]`，注册 `web_search`/`read_url`（stdlib `html.parser` 去标签，无额外依赖）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_search_tools.py
import unittest
from unittest.mock import patch, MagicMock
from tools.search import make_search_tools, html_to_text

class TestSearch(unittest.TestCase):
    def test_html_to_text(self):
        self.assertEqual(html_to_text("<p>a<b>b</b></p>"), "ab")

    def test_read_url(self):
        tools = {t.name: t for t in make_search_tools()}
        with patch("tools.search.requests.get") as get:
            get.return_value = MagicMock(text="<html><body>hello</body></html>")
            out = tools["read_url"].func({"url": "http://x"})
        self.assertIn("hello", out)

    def test_web_search(self):
        tools = {t.name: t for t in make_search_tools()}
        with patch("tools.search.requests.get") as get:
            get.return_value = MagicMock(text='<a class="result__a" href="http://x">T</a><a class="result__snippet">S</a>')
            out = tools["web_search"].func({"query": "q"})
        self.assertIn("T", out)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_search_tools -v`
Expected: FAIL

- [ ] **Step 3: 写 tools/search.py**

```python
import re
from html.parser import HTMLParser
import requests
from tools import Tool

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def html_to_text(html: str) -> str:
    p = _TextExtractor(); p.feed(html)
    return re.sub(r"\s+", " ", "".join(p.parts)).strip()

def make_search_tools() -> list[Tool]:
    def web_search(args):
        q = args["query"]
        r = requests.get("https://html.duckduckgo.com/html/", params={"q": q}, timeout=30)
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', r.text)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text)
        return "\n".join(f"{html_to_text(t)} — {html_to_text(s)}" for t, s in zip(titles, snippets)[:8]) or "（无结果）"

    def read_url(args):
        r = requests.get(args["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        return html_to_text(r.text)[:4000]

    return [
        Tool("web_search", "DuckDuckGo 搜索", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, web_search),
        Tool("read_url", "抓取网页转纯文本", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, read_url),
    ]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_search_tools -v`
Expected: PASS（3 passed）

- [ ] **Step 5: commit**

```bash
git add tools/search.py tests/test_search_tools.py
git commit -m "feat: web search and url reader tools"
```

---

### Task 10: skills 加载器 + 内置 spreadsheet skill

**Files:**
- Create: `skills.py`
- Create: `skills/spreadsheet/SKILL.md`
- Test: `tests/test_skills.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `Skill(name: str, description: str, body: str)`
  - `load_skills(skills_dir: Path) -> list[Skill]`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_skills.py
import tempfile, unittest
from pathlib import Path
from skills import load_skills

class TestSkills(unittest.TestCase):
    def test_load(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "x").mkdir()
            (root / "x" / "SKILL.md").write_text(
                "---\nname: x\ndescription: do x\n---\n\n如何做 x。", encoding="utf-8")
            skills = load_skills(root)
            self.assertEqual(skills[0].name, "x")
            self.assertIn("如何做 x", skills[0].body)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_skills -v`
Expected: FAIL

- [ ] **Step 3: 写 skills.py**

```python
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Skill:
    name: str
    description: str
    body: str

_FRONT = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)

def load_skills(skills_dir: Path) -> list[Skill]:
    out = []
    if not skills_dir.exists():
        return out
    for md in sorted(skills_dir.glob("*/SKILL.md")):
        text = md.read_text(encoding="utf-8")
        m = _FRONT.match(text)
        if not m:
            continue
        meta = dict(re.findall(r"(\w+):\s*(.+)", m.group(1)))
        out.append(Skill(meta.get("name", md.parent.name), meta.get("description", ""), m.group(2).strip()))
    return out
```

- [ ] **Step 4: 写 skills/spreadsheet/SKILL.md**

```markdown
---
name: spreadsheet
description: 处理本地 xlsx/csv 表格——读取、改单元格、追加行、看结构。当用户提到"表格/Excel/数据/台账/订单/清单"时使用。
---

调用顺序建议：先 `sheet_list` 找到文件 → `sheet_summary` 看结构 → `sheet_read` 读内容 → 按需 `sheet_write_cell` / `sheet_add_row`。
只处理工作目录内的 `.xlsx` / `.csv`。Apple Numbers 的 `.numbers` 文件不支持，需先导出为 xlsx/csv。
```

- [ ] **Step 5: 跑测试确认通过**

Run: `python -m unittest tests.test_skills -v`
Expected: PASS（1 passed）

- [ ] **Step 6: commit**

```bash
git add skills.py skills/spreadsheet/SKILL.md tests/test_skills.py
git commit -m "feat: skill loader and built-in spreadsheet skill"
```

---

### Task 11: agent.py（编排循环）+ README + 端到端冒烟

**Files:**
- Create: `agent.py`
- Create: `README.md`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: 全部前序模块
- Produces:
  - `Agent(config: LLMConfig, sandbox_root: Path, confirm, strong_confirm)`
  - `Agent.run(user_input: str) -> str`
  - `build_system_prompt(skills: list[Skill]) -> str`（纯函数，便于测试）

- [ ] **Step 1: 写失败测试（用假 LLMClient 打桩）**

```python
# tests/test_agent.py
import unittest
from unittest.mock import patch
from pathlib import Path
from config import LLMConfig
from llm import LLMResult, ToolCall
from skills import Skill
from agent import Agent, build_system_prompt

class TestBuildPrompt(unittest.TestCase):
    def test_includes_skills(self):
        p = build_system_prompt([Skill("spreadsheet", "处理表格", "先 sheet_list")])
        self.assertIn("spreadsheet", p)
        self.assertIn("处理表格", p)

class TestAgent(unittest.TestCase):
    def test_tool_roundtrip(self):
        cfg = LLMConfig("deepseek", "http://x", "k", "m")
        agent = Agent(cfg, Path("workspace"), lambda m: True, lambda m: True)
        agent.llm = _FakeLLM()
        out = agent.run("写入 a.txt 内容 hi")
        self.assertIn("已写入", out)

class _FakeLLM:
    def __init__(self): self.n = 0
    def chat(self, messages, tools=None):
        self.n += 1
        if self.n == 1:
            return LLMResult(None, [ToolCall("t1", "write_file", {"path": "a.txt", "content": "hi"})])
        return LLMResult("已写入", [])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_agent -v`
Expected: FAIL

- [ ] **Step 3: 写 agent.py**

```python
import json
from pathlib import Path
from typing import Callable
from config import LLMConfig
from llm import LLMClient
from permissions import PermissionGate
from session import Session
from skills import Skill, load_skills
from tools import Registry
from tools.files import make_files_tools
from tools.spreadsheet import make_spreadsheet_tools
from tools.shell import make_shell_tools
from tools.search import make_search_tools

def build_system_prompt(skills: list[Skill]) -> str:
    lines = ["你是一个运行在 iPad 本地沙盒里的 AI agent，帮用户处理文件、表格与信息。",
             "规则：所有文件操作限沙盒目录；删除/覆盖/执行 shell 前会经用户确认；不确定就问。",
             "可用的 skills："]
    for s in skills:
        lines.append(f"- {s.name}: {s.description}")
    if skills:
        lines.append("\n各 skill 用法：")
        for s in skills:
            lines.append(f"[{s.name}]\n{s.body}")
    return "\n".join(lines)

class Agent:
    def __init__(self, config: LLMConfig, sandbox_root: Path,
                 confirm: Callable[[str], bool], strong_confirm: Callable[[str], bool]):
        self.llm = LLMClient(config)
        self.gate = PermissionGate(sandbox_root, ("ls", "python3", "ffmpeg", "cat"), confirm, strong_confirm)
        self.registry = Registry()
        for t in (make_files_tools(self.gate) + make_spreadsheet_tools(self.gate)
                  + make_shell_tools(self.gate) + make_search_tools()):
            self.registry.register(t)
        self.skills = load_skills(Path("skills"))
        self.session_path = sandbox_root / ".session.jsonl"
        if self.session_path.exists():
            self.session = Session.load(self.session_path)
        else:
            self.session = Session(build_system_prompt(self.skills), self.session_path)

    def run(self, user_input: str) -> str:
        self.session.add("user", user_input)
        for _ in range(20):  # 最多 20 轮工具调用
            result = self.llm.chat(self.session.to_messages(), self.registry.schemas())
            if result.tool_calls:
                for tc in result.tool_calls:
                    try:
                        out = self.registry.run(tc.name, tc.arguments)
                    except Exception as e:  # noqa: BLE001
                        out = f"工具执行出错：{e}"
                    self.session.add("tool", f"[{tc.name}] {out}")
                continue
            if result.content:
                self.session.add("assistant", result.content)
                self.session.save()
                return result.content
            return "（无输出）"
        return "（达到最大工具轮数）"
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m unittest tests.test_agent -v`
Expected: PASS（2 passed）

- [ ] **Step 5: 全量测试**

Run: `python -m unittest discover -s tests -v`
Expected: 全部 PASS（约 27 个测试）

- [ ] **Step 6: 写 README.md**

```markdown
# ipad-agent

iPad 本地 AI agent：DeepSeek/Qwen/Grok/OpenAI/Claude 等 provider + 文件/表格/搜索工具 + skill + 权限门控 + 会话持久化。纯 Python，可在 Windows 开发、拷入 iPad a-Shell 运行。

## 本机运行
pip install -r requirements.txt
cp .env.example .env   # 填入 PROVIDER 与 LLM_API_KEY
python agent.py

## 部署到 iPad（a-Shell）
pip install requests openpyxl rich python-dotenv
# 放入 agent 目录，运行 python agent.py；SSL 报错时 export SSL_CERT_FILE=$(python -c "import certifi;print(certifi.where())")
```

- [ ] **Step 7: commit**

```bash
git add agent.py README.md tests/test_agent.py
git commit -m "feat: orchestration loop and end-to-end agent"
```

---

## Self-Review

**1. Spec coverage:** 编排循环(T11) / Provider 抽象(T2) / 文件工具(T6) / 表格工具(T7) / 搜索工具(T9) / skill 加载器(T10) / 权限门控(T3) / 会话持久化(T4) / 意图注册表(T5) / shell 工具(T8) / 配置(T1) —— 全部覆盖 spec 第 5–13 节。

**2. Placeholder scan:** 无 TBD/TODO；每个代码步骤含真实代码。

**3. Type consistency:** `LLMConfig`/`LLMClient.chat`/`LLMResult`/`ToolCall`（T2）与 `agent.py` 调用一致；`Tool`/`Registry`（T5）被 T6–T9 与 T11 一致使用；`PermissionGate`（T3）的 `read/write/delete/shell/is_within_root` 签名在 T6–T8 中一致引用；`Skill`/`load_skills`（T10）在 T11 中一致引用。
