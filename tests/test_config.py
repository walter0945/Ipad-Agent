import unittest
from config import load_llm_config, LLMConfig, ConfigError

class TestLoadLLMConfig(unittest.TestCase):
    def test_deepseek_preset(self):
        c = load_llm_config({"LLM_API_KEY": "sk-1"})
        self.assertEqual(c, LLMConfig("deepseek", "https://api.deepseek.com", "sk-1", "deepseek-chat", "deepseek-reasoner"))

    def test_qwen_preset(self):
        c = load_llm_config({"LLM_API_KEY": "sk-2", "PROVIDER": "qwen"})
        self.assertEqual(c.base_url, "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(c.model, "qwen-plus")

    def test_qwen_no_reasoner(self):
        c = load_llm_config({"LLM_API_KEY": "sk-2", "PROVIDER": "qwen"})
        self.assertEqual(c.reasoner_model, "")

    def test_reasoner_override(self):
        c = load_llm_config({"LLM_API_KEY": "k", "LLM_REASONER_MODEL": "my-reasoner"})
        self.assertEqual(c.reasoner_model, "my-reasoner")

    def test_override(self):
        c = load_llm_config({"LLM_API_KEY": "k", "LLM_BASE_URL": "http://localhost:11434/v1", "LLM_MODEL": "llama3"})
        self.assertEqual(c.base_url, "http://localhost:11434/v1")
        self.assertEqual(c.model, "llama3")

    def test_missing_key_raises(self):
        with self.assertRaises(ConfigError):
            load_llm_config({})

    def test_unknown_provider_without_override_raises(self):
        with self.assertRaises(ConfigError):
            load_llm_config({"LLM_API_KEY": "k", "PROVIDER": "nope"})

    def test_custom_base_url_requires_model(self):
        with self.assertRaises(ConfigError) as cm:
            load_llm_config({"LLM_API_KEY": "k", "PROVIDER": "custom",
                             "LLM_BASE_URL": "http://localhost:11434/v1"})
        self.assertIn("LLM_MODEL", str(cm.exception))

    def test_custom_base_url_with_model_ok(self):
        c = load_llm_config({"LLM_API_KEY": "k", "PROVIDER": "custom",
                             "LLM_BASE_URL": "http://localhost:11434/v1", "LLM_MODEL": "llama3"})
        self.assertEqual(c.model, "llama3")

if __name__ == "__main__":
    unittest.main()
