# tests/test_llm.py
import json, unittest
from unittest.mock import patch, MagicMock
import requests
from config import LLMConfig
from llm import LLMClient, LLMResult, ToolCall, LLMAuthError, LLMRateLimitError, LLMError

CFG = LLMConfig("deepseek", "https://api.deepseek.com", "sk-1", "deepseek-chat")

class TestChat(unittest.TestCase):
    def _resp(self, payload):
        m = MagicMock()
        m.status_code = 200
        m.raise_for_status.return_value = None
        m.json.return_value = payload
        return m

    def test_400_includes_body(self):
        resp = self._resp({"error": {"message": "missing field tool_call_id"}})
        resp.status_code = 400
        resp.text = '{"error":{"message":"missing field tool_call_id"}}'
        with patch("llm.requests.post") as post:
            post.return_value = resp
            with self.assertRaises(LLMError) as cm:
                LLMClient(CFG).chat([{"role": "user", "content": "x"}])
        self.assertIn("tool_call_id", str(cm.exception))

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

    def test_timeout_retries_then_succeeds(self):
        ok = self._resp({"choices": [{"message": {"content": "ok"}}]})
        with patch("llm.requests.post") as post:
            post.side_effect = [requests.exceptions.Timeout(), ok]
            with patch("llm.time.sleep") as sleep:
                r = LLMClient(CFG).chat([{"role": "user", "content": "x"}])
        self.assertEqual(r.content, "ok")
        self.assertTrue(sleep.called)

    def test_connection_error_retries_then_succeeds(self):
        ok = self._resp({"choices": [{"message": {"content": "ok"}}]})
        with patch("llm.requests.post") as post:
            post.side_effect = [requests.exceptions.ConnectionError(), ok]
            with patch("llm.time.sleep"):
                r = LLMClient(CFG).chat([{"role": "user", "content": "x"}])
        self.assertEqual(r.content, "ok")

if __name__ == "__main__":
    unittest.main()
