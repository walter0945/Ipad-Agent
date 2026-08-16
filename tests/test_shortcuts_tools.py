import unittest
from pathlib import Path
from unittest.mock import patch
from permissions import PermissionGate
from tools.shortcuts import make_shortcuts_tools


def _tools(confirm=lambda m: True):
    gate = PermissionGate(Path("workspace"), (), confirm, lambda m: True)
    return {t.name: t for t in make_shortcuts_tools(gate)}


class TestShortcuts(unittest.TestCase):
    def test_run_shortcut_builds_encoded_url(self):
        t = _tools()
        with patch("tools.shortcuts.subprocess.run") as run:
            out = t["run_shortcut"].func({"name": "导出草稿", "input": "hello world"})
        argv = run.call_args[0][0]
        self.assertEqual(argv[0], "open")
        self.assertIn("shortcuts://run-shortcut", argv[1])
        self.assertNotIn(" ", argv[1])          # 空格已被 URL 编码
        self.assertIn("已触发", out)

    def test_run_shortcut_denied_without_confirm(self):
        t = _tools(confirm=lambda m: False)
        with patch("tools.shortcuts.subprocess.run") as run:
            out = t["run_shortcut"].func({"name": "X"})
        run.assert_not_called()
        self.assertIn("拒绝", out)

    def test_open_url_gated(self):
        t = _tools(confirm=lambda m: False)
        with patch("tools.shortcuts.subprocess.run") as run:
            out = t["open_url"].func({"url": "mailto:a@b.com"})
        run.assert_not_called()
        self.assertIn("拒绝", out)

    def test_open_url_runs_when_confirmed(self):
        t = _tools()
        with patch("tools.shortcuts.subprocess.run") as run:
            out = t["open_url"].func({"url": "shortcuts://"})
        run.assert_called_once()
        self.assertIn("已打开", out)

    def test_missing_open_binary_is_graceful(self):
        t = _tools()
        with patch("tools.shortcuts.subprocess.run", side_effect=FileNotFoundError()):
            out = t["run_shortcut"].func({"name": "X"})
        self.assertIn("无法调用", out)


if __name__ == "__main__":
    unittest.main()
