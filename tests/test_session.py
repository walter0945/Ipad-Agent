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

    def test_compress_preserves_base_system_prompt(self):
        s = Session("BASE_RULES_AND_SKILLS")
        for i in range(20):
            s.add("user", f"msg-{i}")
        s.maybe_compress(lambda text: "摘要", max_tokens=50)
        self.assertEqual(s.to_messages()[0]["content"], "BASE_RULES_AND_SKILLS")

    def test_compress_no_orphan_tool_message(self):
        s = Session("sys")
        s.add("user", "处理这批表格")
        for r in range(4):
            s.add("assistant", "", tool_calls=[
                {"id": f"r{r}c{c}", "type": "function",
                 "function": {"name": "sheet_read", "arguments": "{}"}} for c in range(3)])
            for c in range(3):
                s.add("tool", "x" * 300, tool_call_id=f"r{r}c{c}")
        s.maybe_compress(lambda text: "摘要", max_tokens=200)
        msgs = s.to_messages()
        # 每个 tool 消息前面都必须能找到带其 id 的 assistant.tool_calls
        for i, m in enumerate(msgs):
            if m["role"] != "tool":
                continue
            owner = None
            for j in range(i - 1, -1, -1):
                if msgs[j].get("tool_calls"):
                    owner = any(tc["id"] == m["tool_call_id"] for tc in msgs[j]["tool_calls"])
                    break
                if msgs[j]["role"] != "tool":
                    break
            self.assertTrue(owner, f"孤儿 tool 消息 @ {i}: {m['tool_call_id']}")

    def test_compress_skips_on_empty_summary(self):
        s = Session("sys")
        for i in range(20):
            s.add("user", f"msg-{i}")
        before = len(s.to_messages())
        s.maybe_compress(lambda text: "", max_tokens=50)   # 摘要失败
        self.assertEqual(len(s.to_messages()), before)      # 历史一条不丢

    def test_add_tool_calls_and_id(self):
        s = Session("sys")
        s.add("assistant", "", tool_calls=[{"id": "t1", "type": "function",
                                            "function": {"name": "read_file", "arguments": "{}"}}])
        s.add("tool", "[read_file] ok", tool_call_id="t1")
        msgs = s.to_messages()
        self.assertEqual(msgs[1]["tool_calls"][0]["id"], "t1")
        self.assertEqual(msgs[2]["tool_call_id"], "t1")
        self.assertNotIn("tool_calls", msgs[2])
        self.assertNotIn("tool_call_id", msgs[1])

    def test_sanitize_drops_orphan_tools(self):
        # 模拟历史遗留的脏会话：tool 消息的 tool_call_id 对不上前面 assistant 的 tool_calls
        s = Session("sys")
        s.add("assistant", "", tool_calls=[{"id": "a", "type": "function",
                                            "function": {"name": "x", "arguments": "{}"}}])
        s.add("tool", "合法结果", tool_call_id="a")
        s.add("tool", "孤儿", tool_call_id="b")   # b 不属于任何 assistant.tool_calls
        msgs = s.to_messages()
        roles = [(m.get("role"), m.get("tool_call_id")) for m in msgs]
        self.assertIn(("tool", "a"), roles)
        self.assertNotIn(("tool", "b"), roles)

    def test_sanitize_keeps_multi_tool_turn(self):
        s = Session("sys")
        s.add("assistant", "", tool_calls=[
            {"id": "a", "type": "function", "function": {"name": "x", "arguments": "{}"}},
            {"id": "b", "type": "function", "function": {"name": "y", "arguments": "{}"}},
        ])
        s.add("tool", "ra", tool_call_id="a")
        s.add("tool", "rb", tool_call_id="b")
        self.assertEqual(len([m for m in s.to_messages() if m.get("role") == "tool"]), 2)

    def test_roundtrip_with_tool_fields(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.jsonl"
            s = Session("sys", p)
            s.add("assistant", "", tool_calls=[{"id": "t1", "function": {"name": "x", "arguments": "{}"}}])
            s.add("tool", "out", tool_call_id="t1")
            s.save()
            s2 = Session.load(p)
            self.assertEqual(s2.messages[1]["tool_calls"][0]["id"], "t1")
            self.assertEqual(s2.messages[2]["tool_call_id"], "t1")

if __name__ == "__main__":
    unittest.main()
