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


class AlignmentApplyCorpusTest(unittest.TestCase):
    def test_rewrites_fake_exam_template_and_downgrades_tag(self):
        mod = load_module("alignment_apply_corpus.py", "alignment_apply_corpus")
        text = """
---
pos: n.
word_freq: 必备词
semantic_field: 社会专业
---

## 真题/语料关联

> [!example]- 语料
> - The report highlights the importance of author in the final decision. `[真题]`
> - The author argues that the current education system fails to prepare students for the real world. `[例]`
> - She authored several influential papers on climate change during her career. `[例]`
"""
        new_text, stats = mod.repair_corpus_text(text, "author", "必备词", "n.", "社会专业")
        self.assertNotIn("importance of author in the final decision", new_text)
        self.assertNotIn("`[真题]`", new_text)
        self.assertIn("author", new_text.lower())
        self.assertGreaterEqual(stats["rewritten"], 1)

    def test_function_word_uses_real_pattern_not_template(self):
        mod = load_module("alignment_apply_corpus.py", "alignment_apply_corpus")
        text = """
---
pos: conj.
word_freq: 基础词
semantic_field: 抽象关系
---

## 真题/语料关联

> [!example]- 语料
> - The article examines how if can shape public policy. `[真题]`
> - The committee discussed the latest if during the meeting. `[真题]`
> - The report highlights the importance of if in the final decision. `[真题]`
"""
        new_text, stats = mod.repair_corpus_text(text, "if", "基础词", "conj.", "抽象关系")
        self.assertIn("If the evidence is weak, the committee will postpone the decision. `[例]`", new_text)
        self.assertIn("Even if the plan is costly, some voters still support it. `[例]`", new_text)
        self.assertNotIn("importance of if", new_text)
        self.assertGreaterEqual(stats["rewritten"], 3)

    def test_concrete_noun_uses_semantic_scene_instead_of_abstract_template(self):
        mod = load_module("alignment_apply_corpus.py", "alignment_apply_corpus")
        text = """
---
pos: n.
word_freq: 超纲词
semantic_field: 自然物理
---

## 真题/语料关联

> [!example]- 语料
> - The committee discussed the latest redwood during the meeting. `[例]`
> - The report highlights the importance of redwood in the final decision. `[例]`
"""
        new_text, stats = mod.repair_corpus_text(text, "redwood", "超纲词", "n.", "自然物理")
        self.assertIn("The hikers rested under a towering redwood near the coastal trail. `[例]`", new_text)
        self.assertNotIn("latest redwood during the meeting", new_text)
        self.assertNotIn("importance of redwood", new_text)
        self.assertGreaterEqual(stats["rewritten"], 2)

    def test_fixes_space_before_punctuation_and_tops_up_count(self):
        mod = load_module("alignment_apply_corpus.py", "alignment_apply_corpus")
        text = """
---
pos: adj.
word_freq: 超纲词
---

## 真题/语料关联

> [!example]- 语料
> - The 1990s saw a huge increase in the numbers of low-cost airlines . `[例]`
"""
        new_text, stats = mod.repair_corpus_text(text, "low-cost", "超纲词", "adj.", "")
        self.assertIn("low-cost airlines. `[例]`", new_text)
        self.assertEqual(stats["final_count"], 2)
        self.assertGreaterEqual(stats["top_up_added"], 1)

    def test_rewrites_mcq_fragment_into_full_sentence(self):
        mod = load_module("alignment_apply_corpus.py", "alignment_apply_corpus")
        text = """
---
pos: n.
word_freq: 超纲词
---

## 真题/语料关联

> [!example]- 语料
> - According to Branch, state-level science standards in the US __ _ A. call for regular revision B. require urgent application C. have limited influence D. cater to local needs 25. `[真题]`
> - These proposals will need a lot of revision. `[例]`
"""
        new_text, stats = mod.repair_corpus_text(text, "revision", "超纲词", "n.", "")
        self.assertNotIn("According to Branch", new_text)
        self.assertIn("revision", new_text.lower())
        self.assertEqual(stats["rewritten"], 1)
        self.assertEqual(stats["final_count"], 2)

    def test_keeps_valid_entries_without_duplication(self):
        mod = load_module("alignment_apply_corpus.py", "alignment_apply_corpus")
        text = """
---
pos: vt.
word_freq: 必备词
---

## 真题/语料关联

> [!example]- 语料
> - The government abandoned the project after months of delay. `[例]`
> - The government abandoned the project after months of delay. `[例]`
> - Many elderly people feel abandoned by their families. `[例]`
"""
        new_text, stats = mod.repair_corpus_text(text, "abandon", "必备词", "vt.", "")
        self.assertEqual(stats["deduped"], 1)
        self.assertEqual(stats["final_count"], 3)
        self.assertIn("Many elderly people feel abandoned by their families. `[例]`", new_text)


if __name__ == "__main__":
    unittest.main()
