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


class P2TemplateBrowserNormalizeTest(unittest.TestCase):
    def test_normalizes_browser_hit_and_requires_url(self):
        mod = load_module("p2_template_browser_normalize.py", "p2_template_browser_normalize")
        hit = {
            "scope_id": "p2-0001",
            "relpath": "Wiki/L0_单词集合/ability.md",
            "word": "ability",
            "sentence": " Students need the ability to analyze data from different sources. ",
            "tag": "[例]",
            "source": "Browser",
            "url": "https://dictionary.cambridge.org/example/english/ability",
            "acquisition_mode": "browser",
        }
        norm = mod.normalize_browser_hit(hit)
        self.assertEqual(norm["sentence"], "Students need the ability to analyze data from different sources.")
        self.assertEqual(norm["scope_id"], "p2-0001")

        bad = dict(hit)
        bad["url"] = ""
        self.assertIsNone(mod.normalize_browser_hit(bad))


if __name__ == "__main__":
    unittest.main()
