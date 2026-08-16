import unittest
from unittest.mock import patch
from pathlib import Path
from config import LLMConfig
from llm import LLMResult, ToolCall
from skills import Skill
from agent import Agent, build_system_prompt, Confirmer

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

    def test_persist_false_starts_fresh(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sf = root / ".session.jsonl"
            sf.write_text('{"role": "system", "content": "OLD"}\n', encoding="utf-8")
            cfg = LLMConfig("deepseek", "http://x", "k", "m")
            agent = Agent(cfg, root, lambda m: True, lambda m: True, persist=False)
            # 不加载旧会话
            self.assertTrue(all("OLD" not in m["content"] for m in agent.session.to_messages()))
            # 保存是 no-op：旧文件内容不变
            agent.session.save()
            self.assertEqual(sf.read_text(encoding="utf-8"), '{"role": "system", "content": "OLD"}\n')

class TestConfirmer(unittest.TestCase):
    def test_approve_this(self):
        c = Confirmer()
        with patch("builtins.input", return_value="1"):
            self.assertTrue(c.confirm("确认写入？"))
        self.assertFalse(c.approve_all)

    def test_approve_all_then_auto(self):
        c = Confirmer()
        with patch("builtins.input", return_value="2"):
            self.assertTrue(c.strong_confirm("确认删除？"))
        self.assertTrue(c.approve_all)
        with patch("builtins.input") as inp:
            self.assertTrue(c.confirm("再写一次？"))
            inp.assert_not_called()

    def test_reject(self):
        c = Confirmer()
        with patch("builtins.input", return_value="3"):
            self.assertFalse(c.confirm("确认写入？"))
        self.assertFalse(c.approve_all)


class _FakeLLM:
    def __init__(self): self.n = 0
    def chat(self, messages, tools=None, model=None):
        self.n += 1
        if self.n == 1:
            return LLMResult(None, [ToolCall("t1", "write_file", {"path": "a.txt", "content": "hi"})])
        return LLMResult("已写入", [])

if __name__ == "__main__":
    unittest.main()
