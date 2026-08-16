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
