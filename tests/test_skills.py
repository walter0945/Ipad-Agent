# tests/test_skills.py
import tempfile, unittest
from pathlib import Path
from skills import load_skills

class TestSkills(unittest.TestCase):
    def test_load(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "x").mkdir()
            (root / "x" / "SKILL.md").write_text(
                "---\nname: x\ndescription: do x\n---\n\n如何做 x。", encoding="utf-8")
            skills = load_skills(root)
            self.assertEqual(skills[0].name, "x")
            self.assertIn("如何做 x", skills[0].body)

if __name__ == "__main__":
    unittest.main()
