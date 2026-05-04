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


class P2TemplateValidateTest(unittest.TestCase):
    def test_validate_text_rejects_template_corpus(self):
        mod = load_module("p2_template_validate.py", "p2_template_validate")
        text = """
---
word_freq: 必备词
pos: n.
semantic_field: 抽象关系
---

## 真题/语料关联

> [!example]- 语料
> - The report highlights the importance of ability in the final decision. `[例]`
> - Students need the ability to analyze data from different sources. `[例]`
> - She showed remarkable ability in solving complex design problems. `[例]`
"""
        errors = mod.validate_text(text, "ability", "必备词")
        self.assertIn("entry_1_template_corpus", errors)


if __name__ == "__main__":
    unittest.main()
