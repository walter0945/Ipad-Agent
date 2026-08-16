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

if __name__ == "__main__":
    unittest.main()
