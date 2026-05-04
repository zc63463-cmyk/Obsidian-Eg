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


class AlignmentNormalizeStructureTest(unittest.TestCase):
    def test_removes_old_template_fields_but_keeps_core_content(self):
        mod = load_module("alignment_normalize_structure.py", "alignment_normalize_structure")
        text = """---
title: "revision"
tags:
  - 学习/英语/词汇
  - 掌握/L0
mastery: L0
word_freq: 超纲词
---

## 核心释义

**n.** ①==**修订，修改**== `N`；

## 真题/语料关联

> [!example]- 语料 · L3
> - These proposals will need a lot of revision. `[例]`

## 复习记录

> [!note]- 复习追踪
> **上次复习**：2026-04-25
"""
        new_text, changed = mod.normalize_structure(text)
        self.assertTrue(changed)
        self.assertNotIn("mastery: L0", new_text)
        self.assertNotIn("掌握/L0", new_text)
        self.assertNotIn("> [!example]- 语料 · L3", new_text)
        self.assertIn("> [!example]- 语料", new_text)
        self.assertNotIn("## 复习记录", new_text)
        self.assertIn("**n.** ①==**修订，修改**== `N`；", new_text)
        self.assertIn("> - These proposals will need a lot of revision. `[例]`", new_text)

    def test_returns_unchanged_when_already_normalized(self):
        mod = load_module("alignment_normalize_structure.py", "alignment_normalize_structure")
        text = """---
title: "abandon"
tags:
  - 学习/英语/词汇
word_freq: 必备词
---

## 真题/语料关联

> [!example]- 语料
> - The government abandoned the project after months of delay. `[例]`
"""
        new_text, changed = mod.normalize_structure(text)
        self.assertFalse(changed)
        self.assertEqual(new_text, text)


if __name__ == "__main__":
    unittest.main()
