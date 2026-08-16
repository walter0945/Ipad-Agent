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

    def test_secret_files_filtered_from_listing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".env").write_text("KEY=1", encoding="utf-8")
            (root / "a.txt").write_text("hi", encoding="utf-8")
            t = _tools(root)
            out = t["list_dir"].func({"path": "."})
            self.assertIn("a.txt", out)
            self.assertNotIn(".env", out)

    def test_secret_file_unreadable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "secret.pem").write_text("x", encoding="utf-8")
            t = _tools(root)
            out = t["read_file"].func({"path": "secret.pem"})
            self.assertIn("拒绝", out)

    def test_overwrite_uses_strong_confirm(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("old", encoding="utf-8")
            gate = PermissionGate(root, (), lambda m: True, lambda m: False)
            t = {tool.name: tool for tool in make_files_tools(gate)}
            out = t["write_file"].func({"path": "a.txt", "content": "new"})
            self.assertIn("拒绝", out)
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "old")

    def test_overwrite_allowed_with_strong_confirm(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("old", encoding="utf-8")
            t = _tools(root)
            t["write_file"].func({"path": "a.txt", "content": "new"})
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "new")

    def test_read_directory_returns_hint(self):
        with tempfile.TemporaryDirectory() as d:
            t = _tools(Path(d))
            out = t["read_file"].func({"path": "."})
            self.assertIn("是目录，请用 list_dir", out)

    def test_read_large_file_denied(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "big.txt").write_text("x" * (300 * 1024), encoding="utf-8")
            t = _tools(root)
            out = t["read_file"].func({"path": "big.txt"})
            self.assertIn("文件过大", out)

    def test_read_start_at_least_one(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("l1\nl2\nl3", encoding="utf-8")
            t = _tools(root)
            out = t["read_file"].func({"path": "a.txt", "start": 0})
            self.assertIn("l1", out)

    def test_delete_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            t = _tools(root)
            t["write_file"].func({"path": "a.txt", "content": "x"})
            out = t["delete_file"].func({"path": "a.txt"})
            self.assertIn("已删除", out)
            self.assertFalse((root / "a.txt").exists())

    def test_delete_requires_strong_confirm(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("x", encoding="utf-8")
            gate = PermissionGate(root, (), lambda m: True, lambda m: False)
            t = {tool.name: tool for tool in make_files_tools(gate)}
            out = t["delete_file"].func({"path": "a.txt"})
            self.assertIn("拒绝", out)
            self.assertTrue((root / "a.txt").exists())

if __name__ == "__main__":
    unittest.main()
