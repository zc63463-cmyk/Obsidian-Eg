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


class GlobalCorpusValidateTest(unittest.TestCase):
    def test_validate_text_reports_missing_metadata(self):
        mod = load_module("global_corpus_validate.py", "global_corpus_validate")
        text = """---
word_freq: 必备词
pos: n.
semantic_field: 抽象关系
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

    def test_validate_text_rejects_browser_as_source_name(self):
        mod = load_module("global_corpus_validate.py", "global_corpus_validate")
        text = """---
word_freq: 必备词
pos: n.
semantic_field: 抽象关系
---

## 真题/语料关联

> [!example]- 语料
> - Students need the ability to analyze data from different sources. `[例]`
>   - 中译：学生需要具备分析不同来源数据的能力。
>   - 来源：Browser | https://example.com/1
> - She showed remarkable ability in solving complex design problems. `[例]`
>   - 中译：她在解决复杂设计问题时展现出非凡能力。
>   - 来源：Cambridge | https://example.com/2
> - The course develops students' ability to evaluate evidence critically. `[例]`
>   - 中译：这门课程培养学生批判性评估证据的能力。
>   - 来源：Oxford | https://example.com/3
"""
        errors = mod.validate_text(text, "ability", "必备词")
        self.assertIn("entry_1_source_name_is_browser", errors)


if __name__ == "__main__":
    unittest.main()
