import json
import tempfile
import unittest
from pathlib import Path
from permissions import PermissionGate
from tools.video import make_video_tools


class TestVideoTools(unittest.TestCase):
    def test_render_video(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            gate = PermissionGate(root, (), lambda m: True, lambda m: True)
            tool = {t.name: t for t in make_video_tools(gate)}["render_video"]
            storyboard = json.dumps({"scenes": [
                {"text": "Hello", "duration": 0.5},
                {"text": "World", "duration": 0.5},
            ]})
            out = tool.func({"storyboard": storyboard, "output": "out.mp4",
                             "fps": 10, "width": 320, "height": 240})
            self.assertIn("已生成", out)
            self.assertTrue((root / "out.mp4").exists())
            self.assertGreater((root / "out.mp4").stat().st_size, 100)

    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as d:
            gate = PermissionGate(Path(d), (), lambda m: True, lambda m: True)
            tool = {t.name: t for t in make_video_tools(gate)}["render_video"]
            out = tool.func({"storyboard": "not json", "output": "x.mp4"})
            self.assertIn("JSON", out)


if __name__ == "__main__":
    unittest.main()
