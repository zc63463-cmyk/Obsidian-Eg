import importlib.util
import unittest
from pathlib import Path


SCRIPTS = Path("/workspace/Obsidian-Eg/.trae/scripts")


def load_module(filename: str, module_name: str):
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GlobalCorpusBrowserNormalizeTest(unittest.TestCase):
    def test_requires_translation_real_source_and_url(self):
        mod = load_module("global_corpus_browser_normalize.py", "global_corpus_browser_normalize")
        hit = {
            "scope_id": "g-0001",
            "relpath": "Wiki/L0_单词集合/ability.md",
            "word": "ability",
            "sentence": " Students need the ability to analyze data from different sources. ",
            "translation": "学生需要具备分析不同来源数据的能力。",
            "tag": "[例]",
            "source": "Cambridge",
            "url": "https://dictionary.cambridge.org/example/english/ability",
        }
        norm = mod.normalize_browser_hit(hit)
        self.assertEqual(norm["translation"], "学生需要具备分析不同来源数据的能力。")
        bad = dict(hit)
        bad["translation"] = ""
        self.assertIsNone(mod.normalize_browser_hit(bad))
        bad2 = dict(hit)
        bad2["source"] = "Browser"
        self.assertIsNone(mod.normalize_browser_hit(bad2))


if __name__ == "__main__":
    unittest.main()
