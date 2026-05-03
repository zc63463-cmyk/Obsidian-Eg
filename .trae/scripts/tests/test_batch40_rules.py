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


class Batch40ValidateRulesTest(unittest.TestCase):
    def test_accepts_real_tags_beyond_example(self):
        mod = load_module("batch40_validate.py", "batch40_validate")
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[例]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[真题]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[考研-2023-阅读]`"))

    def test_rejects_mcq_fragment_but_accepts_full_sentence(self):
        mod = load_module("batch40_validate.py", "batch40_validate")
        good = "The government refused to subsidize inefficient factories any longer."
        bad = (
            "According to the passage, the policy is to __ A. reduce spending "
            "B. reward waste C. ignore evidence D. raise taxes 27."
        )
        self.assertTrue(mod.looks_like_full_sentence(good))
        self.assertFalse(mod.looks_like_full_sentence(bad))

    def test_hyphenated_word_variants_count_as_hits(self):
        mod = load_module("batch40_validate.py", "batch40_validate")
        self.assertTrue(mod.keep_if_contains_word("think-tank", "The report came from a respected think-tank."))
        self.assertTrue(mod.keep_if_contains_word("think-tank", "The report came from a respected think tank."))
        self.assertTrue(mod.keep_if_contains_word("toll-free", "Customers can call the toll free number for help."))


class Batch40RangeCheckRulesTest(unittest.TestCase):
    def test_allows_subset_word_changes_and_batch_aux_files(self):
        mod = load_module("batch40_range_check.py", "batch40_range_check")
        batch = {
            "Wiki/L0_超纲词/subconscious.md",
            "Wiki/L0_超纲词/subsidize.md",
        }
        mods = {
            "Wiki/L0_超纲词/subconscious.md",
            ".trae/scripts/batch40_apply.py",
            ".trae/batches/batch40_files.txt",
            ".trae/reports/第40批次超纲词901-1000_6.5-6.6_处理报告.md",
        }
        extra_words, extra_other = mod.classify_out_of_scope_modifications(mods, batch)
        self.assertEqual(extra_words, [])
        self.assertEqual(extra_other, [])


if __name__ == "__main__":
    unittest.main()
