import unittest
from pathlib import Path
from permissions import PermissionGate
from tools.shell import make_shell_tools, split_commands

class TestShell(unittest.TestCase):
    def test_split_commands(self):
        self.assertEqual(split_commands("echo a && echo b"), ["echo a", "echo b"])

    def test_block_pipe(self):
        gate = PermissionGate(Path("workspace"), ("echo",), lambda m: True, lambda m: True)
        tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
        self.assertIn("拒绝", tool.func({"command": "echo a | grep b"}))

    def test_run_allowed(self):
        gate = PermissionGate(Path("workspace"), ("echo",), lambda m: True, lambda m: True)
        tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
        self.assertIn("hi", tool.func({"command": "echo hi"}))

    def test_run_and_chain(self):
        gate = PermissionGate(Path("workspace"), ("echo",), lambda m: True, lambda m: True)
        tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
        out = tool.func({"command": "echo a && echo b"})
        self.assertIn("a", out)
        self.assertIn("b", out)

if __name__ == "__main__":
    unittest.main()
