import tempfile
import unittest
from pathlib import Path
from index import build_index


class TestIndex(unittest.TestCase):
    def test_lists_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("x")
            (root / "sub").mkdir()
            (root / "sub" / "b.csv").write_text("y")
            out = build_index(root)
            self.assertIn("a.txt", out)
            self.assertIn("sub/b.csv", out)

    def test_skips_hidden_and_secret(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".env").write_text("secret")
            (root / "credentials").write_text("secret")
            (root / "ok.txt").write_text("x")
            out = build_index(root)
            self.assertNotIn(".env", out)
            self.assertNotIn("credentials", out)
            self.assertIn("ok.txt", out)

    def test_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("空", build_index(Path(d)))


if __name__ == "__main__":
    unittest.main()
