import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from skill_install import parse_frontmatter, install_skill


class TestParseFrontmatter(unittest.TestCase):
    def test_parse(self):
        meta, body = parse_frontmatter("---\nname: my-skill\ndescription: 做某事\n---\n\n正文内容")
        self.assertEqual(meta["name"], "my-skill")
        self.assertEqual(meta["description"], "做某事")
        self.assertEqual(body, "正文内容")

    def test_no_frontmatter(self):
        meta, body = parse_frontmatter("只有正文")
        self.assertEqual(meta, {})
        self.assertEqual(body, "只有正文")


class TestInstallSkill(unittest.TestCase):
    def test_install(self):
        with tempfile.TemporaryDirectory() as d:
            skills_dir = Path(d) / "skills"
            with patch("skill_install.fetch_skill_text") as fetch:
                fetch.return_value = "---\nname: foo\ndescription: bar\n---\n\n说明"
                msg = install_skill("https://github.com/x/foo", skills_dir)
            self.assertIn("foo", msg)
            self.assertTrue((skills_dir / "foo" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
