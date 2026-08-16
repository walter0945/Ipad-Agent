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
