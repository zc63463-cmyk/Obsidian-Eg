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


class P2TemplateScopeTest(unittest.TestCase):
    def test_extracts_only_template_corpus_files(self):
        mod = load_module("p2_template_scope.py", "p2_template_scope")
        audit_items = [
            {
                "relpath": "Wiki/L0_单词集合/ability.md",
                "word": "ability",
                "word_freq": "必备词",
                "problems": ["entry_1_template_corpus", "entry_2_template_corpus", "output_placeholder_residue"],
            },
            {
                "relpath": "Wiki/L0_基础词/if.md",
                "word": "if",
                "word_freq": "基础词",
                "problems": ["output_placeholder_residue"],
            },
            {
                "relpath": "Wiki/L0_超纲词/redwood.md",
                "word": "redwood",
                "word_freq": "超纲词",
                "problems": ["entry_1_template_corpus"],
            },
        ]
        items = mod.build_p2_scope(audit_items)
        self.assertEqual([item["relpath"] for item in items], [
            "Wiki/L0_单词集合/ability.md",
            "Wiki/L0_超纲词/redwood.md",
        ])
        by_path = {item["relpath"]: item for item in items}
        self.assertEqual(by_path["Wiki/L0_单词集合/ability.md"]["problem_entries"], [1, 2])
        self.assertEqual(by_path["Wiki/L0_单词集合/ability.md"]["required_count"], 3)
        self.assertEqual(by_path["Wiki/L0_超纲词/redwood.md"]["required_count"], 2)


if __name__ == "__main__":
    unittest.main()
