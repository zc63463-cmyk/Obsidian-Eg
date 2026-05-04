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


class AlignmentScanRulesTest(unittest.TestCase):
    def test_detects_old_template_residue(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """---
mastery: L0
tags:
  - 学习/英语/词汇
  - 掌握/L0
---

> [!example]- 语料 · L3
## 复习记录
"""
        self.assertEqual(
            mod.detect_structure_issues(text),
            ["old_mastery", "old_tag_mastery", "old_callout_level_suffix", "old_review_section"],
        )

    def test_detects_mcq_fragment_and_insufficient_count(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 真题/语料关联

> [!example]- 语料
> - According to Branch, state-level science standards in the US __ _ A. call for regular revision B. require urgent application C. have limited influence D. cater to local needs 25. `[真题]`
> - These proposals will need a lot of revision. `[例]`
"""
        issues = mod.scan_corpus_issues(text, "revision", "超纲词")
        self.assertIn("entry_1_not_full_sentence", issues)
        self.assertIn("entry_1_explanation_or_mcq_residue", issues)

    def test_detects_trailing_space_before_punctuation_and_count_gap(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 真题/语料关联

> [!example]- 语料
> - The 1990s saw a huge increase in the numbers of low-cost airlines . `[例]`
"""
        issues = mod.scan_corpus_issues(text, "low-cost", "超纲词")
        self.assertIn("entry_1_space_before_punctuation", issues)
        self.assertIn("insufficient_corpus_count", issues)

    def test_detects_missing_tag_and_duplicate_sentence(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 真题/语料关联

> [!example]- 语料
> - The government abandoned the project after months of delay.
> - The government abandoned the project after months of delay. `[例]`
> - Many elderly people feel abandoned by their families. `[例]`
"""
        issues = mod.scan_corpus_issues(text, "abandon", "必备词")
        self.assertIn("entry_1_missing_tag", issues)
        self.assertIn("duplicate_sentence", issues)

    def test_y_verb_inflection_does_not_trigger_missing_target_word(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 真题/语料关联

> [!example]- 语料
> - The law embodied a core principle of fairness. `[例]`
> - The report exemplified the trend with clear data. `[例]`
> - The image was magnified on the screen. `[例]`
"""
        embody_issues = mod.scan_corpus_issues(text, "embody", "超纲词")
        exemplify_issues = mod.scan_corpus_issues(text, "exemplify", "超纲词")
        magnify_issues = mod.scan_corpus_issues(text, "magnify", "超纲词")
        self.assertNotIn("entry_1_missing_target_word", embody_issues)
        self.assertNotIn("entry_2_missing_target_word", exemplify_issues)
        self.assertNotIn("entry_3_missing_target_word", magnify_issues)


if __name__ == "__main__":
    unittest.main()
