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


class AlignmentValidateRulesTest(unittest.TestCase):
    def test_accepts_normalized_file(self):
        mod = load_module("alignment_validate.py", "alignment_validate")
        text = """---
title: "low-cost"
tags:
  - 学习/英语/词汇
word_freq: 超纲词
pos: adj.
---

## 核心释义

**adj.** ①==**低成本的**== `adj`；

## 真题/语料关联

> [!example]- 语料
> - The 1990s saw a huge increase in the numbers of low-cost airlines. `[例]`
>   - 中译：20世纪90年代低成本航空公司的数量大幅增加。
>   - 来源：Cambridge | https://example.com/low-cost-1
> - The company adopted a low-cost approach to improve efficiency. `[例]`
>   - 中译：这家公司采用了低成本的方法来提高效率。
>   - 来源：Oxford | https://example.com/low-cost-2
"""
        errors = mod.validate_text(text, "low-cost", "超纲词")
        self.assertEqual(errors, [])

    def test_rejects_old_structure_and_unknown_source(self):
        mod = load_module("alignment_validate.py", "alignment_validate")
        text = """---
title: "revision"
tags:
  - 学习/英语/词汇
  - 掌握/L0
mastery: L0
word_freq: 超纲词
pos: n.
---

## 核心释义

**n.** ①==**修订**== `N`；

## 真题/语料关联

> [!example]- 语料 · L3
> - These proposals will need a lot of revision. `[Unknown]`

## 复习记录
"""
        errors = mod.validate_text(text, "revision", "超纲词")
        self.assertIn("old_mastery", errors)
        self.assertIn("old_tag_mastery", errors)
        self.assertIn("old_callout_level_suffix", errors)
        self.assertIn("old_review_section", errors)
        self.assertIn("entry_1_invalid_tag", errors)
        self.assertIn("insufficient_corpus_count", errors)

    def test_rejects_missing_translation_and_source_metadata(self):
        mod = load_module("alignment_validate.py", "alignment_validate")
        text = """---
title: "ability"
tags:
  - 学习/英语/词汇
word_freq: 必备词
pos: n.
---

## 真题/语料关联

> [!example]- 语料
> - Students need the ability to analyze data from different sources. `[例]`
> - She showed remarkable ability in solving complex design problems. `[例]`
> - The course develops students' ability to evaluate evidence critically. `[例]`
"""
        errors = mod.validate_text(text, "ability", "必备词")
        self.assertIn("entry_1_missing_translation", errors)
        self.assertIn("entry_1_missing_source", errors)
        self.assertIn("entry_1_missing_source_url", errors)


if __name__ == "__main__":
    unittest.main()
