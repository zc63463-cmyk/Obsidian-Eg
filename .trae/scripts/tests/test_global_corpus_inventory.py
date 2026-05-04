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


class GlobalCorpusInventoryTest(unittest.TestCase):
    def test_classifies_verified_backfill_and_exam_refetch_entries(self):
        mod = load_module("global_corpus_inventory.py", "global_corpus_inventory")
        text = """
## 真题/语料关联

> [!example]- 语料
> - Students need the ability to analyze data from different sources. `[例]`
>   - 中译：学生需要具备分析不同来源数据的能力。
>   - 来源：Cambridge | https://dictionary.cambridge.org/example/english/ability
> - She showed remarkable ability in solving complex design problems. `[例]`
> - The report highlights the importance of ability in the final decision. `[例]`
"""
        items = mod.inventory_entries(
            scope_id="g-0001",
            relpath="Wiki/L0_单词集合/ability.md",
            word="ability",
            word_freq="必备词",
            text=text,
        )
        self.assertEqual([item["status"] for item in items], [
            "verified_keep",
            "candidate_preserve_backfill",
            "template_refetch",
        ])
        self.assertEqual(items[0]["entry_id"], "g-0001:e1")
        self.assertEqual(items[0]["preferred_action"], "keep_verified")
        self.assertTrue(items[0]["source_present"])
        self.assertTrue(items[1]["must_external_refetch"])
        self.assertTrue(items[1]["needs_url"])
        self.assertEqual(items[2]["original_tag"], "[例]")
        summary = mod.summarize_file_entries(items)
        self.assertEqual(summary["verified_count"], 1)
        self.assertEqual(summary["actionable_count"], 2)
        self.assertEqual(summary["missing_url_count"], 2)
        self.assertEqual(summary["template_count"], 1)

    def test_missing_url_exam_entry_forces_exam_refetch(self):
        mod = load_module("global_corpus_inventory.py", "global_corpus_inventory")
        text = """
## 真题/语料关联

> [!example]- 语料
> - This was taken from an old exam sentence. `[真题]`
"""
        items = mod.inventory_entries(
            scope_id="g-0002",
            relpath="Wiki/L0_基础词/test.md",
            word="test",
            word_freq="基础词",
            text=text,
        )
        self.assertEqual(items[0]["status"], "unverifiable_exam_refetch")
        self.assertEqual(items[0]["preferred_action"], "external_refetch")
        self.assertTrue(items[0]["must_external_refetch"])


if __name__ == "__main__":
    unittest.main()
