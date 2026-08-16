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
