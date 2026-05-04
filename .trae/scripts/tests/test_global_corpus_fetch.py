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


class GlobalCorpusFetchTest(unittest.TestCase):
    def test_metadata_backfill_candidate_reuses_verified_original_sentence(self):
        mod = load_module("global_corpus_fetch.py", "global_corpus_fetch")
        existing = {
            "entry_id": "g-0001:e1",
            "relpath": "Wiki/L0_单词集合/ability.md",
            "word": "ability",
            "word_freq": "必备词",
            "entry_index": 1,
            "original_sentence": "Students need the ability to analyze data from different sources.",
            "original_tag": "[例]",
            "status": "candidate_preserve_backfill",
        }
        static = [
            {
                "sentence": "Students need the ability to analyze data from different sources.",
                "tag": "[例]",
                "source": "Cambridge",
                "url": "https://dictionary.cambridge.org/example/english/ability",
                "translation": "学生需要具备分析不同来源数据的能力。",
            }
        ]
        out = mod.resolve_entry_from_static_candidates(existing, static, "n.", "抽象关系")
        self.assertEqual(out["sentence"], existing["original_sentence"])
        self.assertEqual(out["source"], "Cambridge")
        self.assertEqual(out["translation"], "学生需要具备分析不同来源数据的能力。")

    def test_unverifiable_old_exam_sentence_is_not_preserved_as_exam(self):
        mod = load_module("global_corpus_fetch.py", "global_corpus_fetch")
        existing = {
            "entry_id": "g-0002:e1",
            "relpath": "Wiki/L0_基础词/test.md",
            "word": "test",
            "word_freq": "基础词",
            "entry_index": 1,
            "original_sentence": "This was taken from an old exam sentence.",
            "original_tag": "[真题]",
            "status": "unverifiable_exam_refetch",
        }
        static = [
            {
                "sentence": "Students took the language test at the end of the term.",
                "tag": "[例]",
                "source": "Oxford",
                "url": "https://www.oxfordlearnersdictionaries.com/definition/english/test",
                "translation": "学生们在学期末参加了语言测试。",
            }
        ]
        out = mod.resolve_entry_from_static_candidates(existing, static, "n.", "抽象关系")
        self.assertEqual(out["tag"], "[例]")
        self.assertNotEqual(out["sentence"], existing["original_sentence"])

    def test_final_entries_follow_inventory_actions(self):
        mod = load_module("global_corpus_fetch.py", "global_corpus_fetch")
        inventory_entries = [
            {
                "entry_id": "g-0001:e1",
                "word": "ability",
                "original_sentence": "Students need the ability to analyze data from different sources.",
                "original_tag": "[例]",
                "status": "verified_keep",
                "preferred_action": "keep_verified",
            },
            {
                "entry_id": "g-0001:e2",
                "word": "ability",
                "original_sentence": "She showed remarkable ability in solving complex design problems.",
                "original_tag": "[例]",
                "status": "candidate_preserve_backfill",
                "preferred_action": "preserve_sentence_and_backfill",
            },
            {
                "entry_id": "g-0001:e3",
                "word": "ability",
                "original_sentence": "The report highlights the importance of ability in the final decision.",
                "original_tag": "[例]",
                "status": "external_refetch",
                "preferred_action": "external_refetch",
            },
        ]
        kept = [
            {
                "sentence": "Students need the ability to analyze data from different sources.",
                "tag": "[例]",
                "translation": "学生需要具备分析不同来源数据的能力。",
                "source": "Cambridge",
                "url": "https://dictionary.cambridge.org/example/english/ability",
            }
        ]
        static = [
            {
                "sentence": "She showed remarkable ability in solving complex design problems.",
                "tag": "[例]",
                "translation": "她在解决复杂设计问题时展现出非凡能力。",
                "source": "Oxford",
                "url": "https://example.com/2",
            },
            {
                "sentence": "The course develops students' ability to evaluate evidence critically.",
                "tag": "[例]",
                "translation": "这门课程培养学生批判性评估证据的能力。",
                "source": "Merriam-Webster",
                "url": "https://example.com/3",
            },
        ]
        out = mod.build_final_entries_for_item(
            inventory_entries=inventory_entries,
            kept_entries=kept,
            static_candidates=static,
            browser_candidates=[],
            word="ability",
            word_freq="必备词",
            pos="n.",
            semantic_field="抽象关系",
        )
        self.assertEqual(len(out["final_entries"]), 3)
        self.assertEqual(out["entry_actions"]["g-0001:e1"], "keep_verified")
        self.assertEqual(out["entry_actions"]["g-0001:e2"], "preserve_sentence_and_backfill")
        self.assertEqual(out["entry_actions"]["g-0001:e3"], "external_refetch")
        self.assertFalse(out["unresolved"])

    def test_browser_candidates_with_browser_source_are_rejected(self):
        mod = load_module("global_corpus_fetch.py", "global_corpus_fetch")
        bad = {
            "sentence": "Students need the ability to analyze data from different sources.",
            "tag": "[例]",
            "translation": "学生需要具备分析不同来源数据的能力。",
            "source": "Browser",
            "url": "https://example.com/1",
        }
        self.assertFalse(mod.global_candidate_allowed(bad, "ability", "n.", "抽象关系"))


if __name__ == "__main__":
    unittest.main()
