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


class Batch41ValidateRulesTest(unittest.TestCase):
    def test_accepts_real_tags_beyond_example(self):
        mod = load_module("batch41_validate.py", "batch41_validate")
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[例]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[真题]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("A clear sentence. `[考研-2023-阅读]`"))

    def test_hyphenated_word_variants_count_as_hits(self):
        mod = load_module("batch41_validate.py", "batch41_validate")
        self.assertTrue(mod.keep_if_contains_word("twenty-first", "It was a major issue in the twenty first century."))


class Batch41MakeListRulesTest(unittest.TestCase):
    def test_tail_batch_boundaries_and_size(self):
        mod = load_module("batch41_make_list.py", "batch41_make_list")
        self.assertEqual(mod.SLICE_START, 1000)
        self.assertEqual(mod.EXPECTED_COUNT, 50)
        self.assertEqual(mod.EXPECTED_FIRST, "unpredictability.md")
        self.assertEqual(mod.EXPECTED_LAST, "yearning.md")


class Batch41RangeCheckRulesTest(unittest.TestCase):
    def test_allows_subset_word_changes_and_batch_aux_files(self):
        mod = load_module("batch41_range_check.py", "batch41_range_check")
        batch = {
            "Wiki/L0_超纲词/unpredictability.md",
            "Wiki/L0_超纲词/yearning.md",
        }
        mods = {
            "Wiki/L0_超纲词/unpredictability.md",
            ".trae/scripts/batch41_apply.py",
            ".trae/batches/batch41_files.txt",
            ".trae/reports/第41批次超纲词1001-1050_6.5-6.6_处理报告.md",
        }
        extra_words, extra_other = mod.classify_out_of_scope_modifications(mods, batch)
        self.assertEqual(extra_words, [])
        self.assertEqual(extra_other, [])


if __name__ == "__main__":
    unittest.main()
