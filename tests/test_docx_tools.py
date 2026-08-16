import tempfile
import unittest
from pathlib import Path
from permissions import PermissionGate
from tools.docx import make_docx_tools


def _tools(root: Path):
    gate = PermissionGate(root, (), lambda m: True, lambda m: True)
    return {t.name: t for t in make_docx_tools(gate)}


class TestDocxTools(unittest.TestCase):
    def test_create_and_read(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            t = _tools(root)
            out = t["docx_create"].func({"path": "r.docx",
                                         "content": "# 标题\n第一段\n## 小标题\n第二段"})
            self.assertIn("已创建", out)
            text = t["docx_read"].func({"path": "r.docx"})
            self.assertIn("标题", text)
            self.assertIn("第一段", text)

    def test_append(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            t = _tools(root)
            t["docx_create"].func({"path": "a.docx", "content": "原文"})
            t["docx_append"].func({"path": "a.docx", "text": "追加段"})
            self.assertIn("追加段", t["docx_read"].func({"path": "a.docx"}))

    def test_replace(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            t = _tools(root)
            t["docx_create"].func({"path": "b.docx", "content": "你好世界"})
            out = t["docx_replace"].func({"path": "b.docx", "old": "世界", "new": "朋友"})
            self.assertIn("已替换", out)
            self.assertIn("你好朋友", t["docx_read"].func({"path": "b.docx"}))

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            t = _tools(Path(d))
            self.assertIn("不存在", t["docx_append"].func({"path": "nope.docx", "text": "x"}))


if __name__ == "__main__":
    unittest.main()
