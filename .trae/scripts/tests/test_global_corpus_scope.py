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


class GlobalCorpusScopeTest(unittest.TestCase):
    def test_builds_full_scope_from_three_vocab_dirs(self):
        mod = load_module("global_corpus_scope.py", "global_corpus_scope")
        relpaths = [
            "Wiki/L0_单词集合/ability.md",
            "Wiki/L0_基础词/time.md",
            "Wiki/L0_超纲词/revision.md",
        ]
        freq_map = {
            "Wiki/L0_单词集合/ability.md": "必备词",
            "Wiki/L0_基础词/time.md": "基础词",
            "Wiki/L0_超纲词/revision.md": "超纲词",
        }
        items = mod.build_global_scope_items(relpaths, freq_map)
        self.assertEqual([item["scope_id"] for item in items], ["g-0001", "g-0002", "g-0003"])
        self.assertEqual([item["relpath"] for item in items], relpaths)
        self.assertEqual(items[0]["word"], "ability")
        self.assertEqual(items[2]["word_freq"], "超纲词")


if __name__ == "__main__":
    unittest.main()
