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


class GlobalAuditRulesTest(unittest.TestCase):
    def test_template_corpus_should_be_flagged(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 真题/语料关联

> [!example]- 语料
> - The report highlights the importance of ability in the final decision. `[例]`
> - The committee discussed the latest ability during the meeting. `[例]`
> - The article examines how ability can shape public policy. `[例]`
"""
        issues = mod.scan_corpus_issues(text, "ability", "必备词", "n.", "抽象关系")
        self.assertIn("entry_1_template_corpus", issues)
        self.assertIn("entry_2_template_corpus", issues)
        self.assertIn("entry_3_template_corpus", issues)

    def test_fake_exam_tag_should_be_flagged(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 真题/语料关联

> [!example]- 语料
> - The report highlights the importance of if in the final decision. `[真题]`
> - The committee discussed the latest if during the meeting. `[真题]`
> - The article examines how if can shape public policy. `[真题]`
"""
        issues = mod.scan_corpus_issues(text, "if", "基础词", "conj.", "抽象关系")
        self.assertIn("entry_1_fake_exam_tag", issues)
        self.assertIn("entry_2_fake_exam_tag", issues)
        self.assertIn("entry_3_fake_exam_tag", issues)

    def test_function_word_invalid_usage_should_be_flagged(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 真题/语料关联

> [!example]- 语料
> - The article examines how if can shape public policy. `[真题]`
> - If the evidence is weak, the committee will postpone the decision. `[例]`
> - Even if the plan is costly, some voters still support it. `[例]`
"""
        issues = mod.scan_corpus_issues(text, "if", "基础词", "conj.", "抽象关系")
        self.assertIn("entry_1_function_word_invalid_usage", issues)
        self.assertNotIn("entry_2_function_word_invalid_usage", issues)
        self.assertNotIn("entry_3_function_word_invalid_usage", issues)

    def test_semantic_mismatch_for_concrete_noun_should_be_flagged(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 真题/语料关联

> [!example]- 语料
> - The committee discussed the latest redwood during the meeting. `[例]`
> - The hikers rested under a towering redwood near the coastal trail. `[例]`
"""
        issues = mod.scan_corpus_issues(text, "redwood", "超纲词", "n.", "自然物理")
        self.assertIn("entry_1_semantic_mismatch", issues)
        self.assertNotIn("entry_2_semantic_mismatch", issues)

    def test_output_placeholder_and_title_drift_should_be_flagged(self):
        mod = load_module("alignment_scan.py", "alignment_scan")
        text = """
## 主动产出

> [!success]- 内化标记
> **写作用例**：<自己在写作/翻译中使用该词的例句>
> **翻译实践**：<翻译练习中的使用记录>
"""
        issues = mod.scan_output_issues(text)
        self.assertIn("noncanonical_output_section_title", issues)
        self.assertIn("output_placeholder_residue", issues)


if __name__ == "__main__":
    unittest.main()
