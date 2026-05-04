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


class P2TemplateApplyTest(unittest.TestCase):
    def test_strict_ready_requires_enough_non_unknown_entries(self):
        mod = load_module("p2_template_apply.py", "p2_template_apply")
        item = {
            "required_count": 3,
            "unresolved": False,
            "final_entries": [
                {"sentence": "A", "tag": "[例]", "source": "Cambridge", "url": "u1", "translation": "甲"},
                {"sentence": "B", "tag": "[例]", "source": "Oxford", "url": "u2", "translation": "乙"},
            ],
        }
        self.assertFalse(mod.strict_ready(item))

        item["final_entries"].append({"sentence": "C", "tag": "[例]", "source": "Unknown", "url": "u3", "translation": "丙"})
        self.assertFalse(mod.strict_ready(item))

    def test_strict_ready_rejects_browser_as_fake_source(self):
        mod = load_module("p2_template_apply.py", "p2_template_apply")
        item = {
            "required_count": 1,
            "unresolved": False,
            "final_entries": [
                {"sentence": "A", "tag": "[例]", "source": "Browser", "url": "u1", "translation": "甲"},
            ],
        }
        self.assertFalse(mod.strict_ready(item))

    def test_build_block_reconstructs_only_corpus_bullets(self):
        mod = load_module("p2_template_apply.py", "p2_template_apply")
        block = mod.build_block("> [!example]- 语料", [
            {"sentence": "Students need the ability to analyze data from different sources.", "tag": "[例]", "translation": "学生需要具备分析不同来源数据的能力。", "source": "Cambridge", "url": "https://example.com/1"},
            {"sentence": "She showed remarkable ability in solving complex design problems.", "tag": "[例]", "translation": "她在解决复杂设计问题时展现出非凡能力。", "source": "Oxford", "url": "https://example.com/2"},
            {"sentence": "The course develops students' ability to evaluate evidence critically.", "tag": "[例]", "translation": "这门课程培养学生批判性评估证据的能力。", "source": "Merriam-Webster", "url": "https://example.com/3"},
        ])
        self.assertIn("> [!example]- 语料", block)
        self.assertEqual(block.count("> - "), 3)
        self.assertEqual(block.count(">   - 中译："), 3)
        self.assertEqual(block.count(">   - 来源："), 3)

    def test_build_block_normalizes_space_before_punctuation(self):
        mod = load_module("p2_template_apply.py", "p2_template_apply")
        block = mod.build_block("> [!example]- 语料", [
            {
                "sentence": "Plants absorb carbon dioxide .",
                "tag": "[例]",
                "translation": "植物会吸收二氧化碳。",
                "source": "Cambridge",
                "url": "https://example.com/co2",
            },
        ])
        self.assertIn("Plants absorb carbon dioxide. `[例]`", block)
        self.assertNotIn("dioxide .", block)
        self.assertIn(">   - 中译：植物会吸收二氧化碳。", block)
        self.assertIn(">   - 来源：Cambridge | https://example.com/co2", block)


if __name__ == "__main__":
    unittest.main()
