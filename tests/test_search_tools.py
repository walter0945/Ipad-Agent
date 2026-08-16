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
