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


class Batch39ValidateRulesTest(unittest.TestCase):
    def test_accepts_real_tags_beyond_example(self):
        mod = load_module("batch39_validate.py", "batch39_validate")
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[例]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[真题]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[考研-2023-阅读]`"))

    def test_rejects_mcq_fragment_but_accepts_full_sentence(self):
        mod = load_module("batch39_validate.py", "batch39_validate")
        good = "New investment helped revitalize the old industrial district."
        bad = (
            "According to Branch, state-level science standards in the US __ _ "
            "A. call for regular revision B. require urgent application "
            "C. have limited influence D. cater to local needs 25."
        )
        self.assertTrue(mod.looks_like_full_sentence(good))
        self.assertFalse(mod.looks_like_full_sentence(bad))


class Batch39RangeCheckRulesTest(unittest.TestCase):
    def test_allows_subset_word_changes_and_batch_aux_files(self):
        mod = load_module("batch39_range_check.py", "batch39_range_check")
        batch = {
            "Wiki/L0_超纲词/revitalize.md",
            "Wiki/L0_超纲词/reviewer.md",
        }
        mods = {
            "Wiki/L0_超纲词/revitalize.md",
            ".trae/scripts/batch39_apply.py",
            ".trae/batches/batch39_files.txt",
            ".trae/reports/第39批次超纲词801-900_6.5-6.6_处理报告.md",
        }
        extra_words, extra_other = mod.classify_out_of_scope_modifications(mods, batch)
        self.assertEqual(extra_words, [])
        self.assertEqual(extra_other, [])

    def test_rejects_out_of_batch_word_changes(self):
        mod = load_module("batch39_range_check.py", "batch39_range_check")
        batch = {"Wiki/L0_超纲词/revitalize.md"}
        mods = {
            "Wiki/L0_超纲词/revitalize.md",
            "Wiki/L0_超纲词/unrelated.md",
        }
        extra_words, extra_other = mod.classify_out_of_scope_modifications(mods, batch)
        self.assertEqual(extra_words, ["Wiki/L0_超纲词/unrelated.md"])
        self.assertEqual(extra_other, [])


if __name__ == "__main__":
    unittest.main()
