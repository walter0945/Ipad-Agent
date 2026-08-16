import unittest
from tools import Registry, Tool

class TestRegistry(unittest.TestCase):
    def test_register_and_run(self):
        r = Registry()
        r.register(Tool("echo", "repeat", {"type": "object", "properties": {"x": {"type": "string"}}},
                        lambda args: args["x"]))
        self.assertEqual(r.run("echo", {"x": "hi"}), "hi")
        self.assertEqual(len(r.schemas()), 1)

    def test_run_unknown_raises(self):
        with self.assertRaises(KeyError):
            Registry().run("nope", {})

if __name__ == "__main__":
    unittest.main()
