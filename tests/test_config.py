import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


def load_config_class():
    config_path = Path(__file__).resolve().parents[1] / "common" / "config.py"
    spec = importlib.util.spec_from_file_location("config_mod", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Config


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.Config = load_config_class()
        self.old_cwd = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self.tmpdir.name)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmpdir.cleanup()

    def write_config(self, content):
        Path("config.yml").write_text(content, encoding="utf8")

    def test_extra_params_defaults_to_empty_mapping(self):
        self.write_config("llm:\n  extra_params:\n")

        config = self.Config()

        self.assertEqual(config.llm_extra_params, {})

    def test_extra_params_accepts_nested_mapping(self):
        self.write_config(
            "llm:\n"
            "  extra_params:\n"
            "    thinking_config:\n"
            "      thinking_budget: 0\n"
        )

        config = self.Config()

        self.assertEqual(
            config.llm_extra_params,
            {"thinking_config": {"thinking_budget": 0}},
        )

    def test_extra_params_rejects_non_mapping(self):
        self.write_config("llm:\n  extra_params: nope\n")

        with self.assertRaises(ValueError):
            self.Config()

    def test_max_tokens_is_loaded_separately_from_max_length(self):
        self.write_config("llm:\n  max_length: 100\n  max_tokens: 200\n")

        config = self.Config()

        self.assertEqual(config.llm_max_length, 100)
        self.assertEqual(config.llm_max_tokens, 200)


if __name__ == "__main__":
    unittest.main()
