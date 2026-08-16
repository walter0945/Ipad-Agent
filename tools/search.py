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
        return "\n".join(f"{html_to_text(t)} — {html_to_text(s)}" for t, s in list(zip(titles, snippets))[:8]) or "（无结果）"

    def read_url(args):
        r = requests.get(args["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        return html_to_text(r.text)[:4000]

    return [
        Tool("web_search", "DuckDuckGo 搜索", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, web_search),
        Tool("read_url", "抓取网页转纯文本", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, read_url),
    ]
