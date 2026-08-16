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


if __name__ == "__main__":
    unittest.main()
