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


class CommonAlignmentRulesTest(unittest.TestCase):
    def test_accepts_extended_valid_tags(self):
        mod = load_module("common_alignment_rules.py", "common_alignment_rules")
        self.assertIsNotNone(mod.VALID_TAG_RE.search("Sentence. `[例]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("Sentence. `[真题]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("Sentence. `[考研-2023-阅读]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("Sentence. `[COCA-ACAD]`"))
        self.assertIsNotNone(mod.VALID_TAG_RE.search("Sentence. `[BNC-SPOKEN]`"))

    def test_hyphenated_and_spaced_variants_both_hit(self):
        mod = load_module("common_alignment_rules.py", "common_alignment_rules")
        self.assertTrue(mod.keep_if_contains_word("low-cost", "Low-cost airlines expanded quickly."))
        self.assertTrue(mod.keep_if_contains_word("low-cost", "Low cost airlines expanded quickly."))
        self.assertTrue(mod.keep_if_contains_word("co-worker", "Her co worker offered help."))
        self.assertTrue(mod.keep_if_contains_word("embody", "The law embodied a core principle of fairness."))
        self.assertTrue(mod.keep_if_contains_word("exemplify", "The report exemplified the trend with clear data."))
        self.assertTrue(mod.keep_if_contains_word("magnify", "The image was magnified on the screen."))
        self.assertTrue(mod.keep_if_contains_word("sow", "Broad beans that were sown in the previous autumn will be ready first."))

    def test_requires_rewrite_for_mcq_fragment_and_short_phrase(self):
        mod = load_module("common_alignment_rules.py", "common_alignment_rules")
        mcq = "According to the passage, the policy is to __ A. reduce spending B. reward waste C. ignore evidence D. raise taxes 27."
        phrase = '"abide by the rules and regulations"'
        ocr_spaced = "T h is m ig h t b e e s p e c ia lly tru e if y o u a re w o rk in g fro m h o m e."
        self.assertTrue(mod.requires_rewrite(mcq))
        self.assertTrue(mod.requires_rewrite(phrase))
        self.assertTrue(mod.requires_rewrite(ocr_spaced))
        self.assertFalse(mod.requires_rewrite("Citizens must abide by the rules and regulations of the community."))
        self.assertFalse(mod.requires_rewrite("A specialist in Japanese history gave the lecture."))
        self.assertFalse(mod.requires_rewrite("You need to see a specialist."))

    def test_flags_explanation_residue_and_space_before_punctuation(self):
        mod = load_module("common_alignment_rules.py", "common_alignment_rules")
        self.assertTrue(mod.has_explanation_residue("The phrase is common —— 考研阅读常见搭配"))
        self.assertTrue(mod.has_space_before_punctuation("The 1990s saw a huge increase in low-cost airlines ."))


if __name__ == "__main__":
    unittest.main()
