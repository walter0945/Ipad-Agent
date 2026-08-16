import unittest
from router import should_use_reasoner


class TestRouter(unittest.TestCase):
    def test_reasoning_triggers(self):
        self.assertTrue(should_use_reasoner("为什么天空是蓝的？"))
        self.assertTrue(should_use_reasoner("帮我分析一下这个方案"))

    def test_simple_does_not_trigger(self):
        self.assertFalse(should_use_reasoner("你好"))
        self.assertFalse(should_use_reasoner("列出文件"))

    def test_empty(self):
        self.assertFalse(should_use_reasoner(""))

    def test_english_hint(self):
        self.assertTrue(should_use_reasoner("analyze this data"))
        self.assertTrue(should_use_reasoner("make a plan for launch"))
        self.assertTrue(should_use_reasoner("design a schema"))

    def test_english_substring_no_false_trigger(self):
        # "plan" 不应命中 "airplane"，"reason" 不应命中 "seasoning"
        self.assertFalse(should_use_reasoner("book an airplane ticket"))
        self.assertFalse(should_use_reasoner("add more seasoning"))


if __name__ == "__main__":
    unittest.main()
