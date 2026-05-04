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


class GlobalCorpusBatchFillTest(unittest.TestCase):
    def test_chunk_items_splits_preserving_order(self):
        mod = load_module("global_corpus_batch_fill.py", "global_corpus_batch_fill")
        out = mod.chunk_items([1, 2, 3, 4, 5], 2)
        self.assertEqual(out, [[1, 2], [3, 4], [5]])

    def test_selects_only_metadata_bad_files_up_to_limit(self):
        mod = load_module("global_corpus_batch_fill.py", "global_corpus_batch_fill")
        scope_items = [
            {"scope_id": "g-0001", "relpath": "Wiki/L0_超纲词/a.md", "word": "a", "required_count": 2},
            {"scope_id": "g-0002", "relpath": "Wiki/L0_超纲词/b.md", "word": "b", "required_count": 2},
            {"scope_id": "g-0003", "relpath": "Wiki/L0_超纲词/c.md", "word": "c", "required_count": 2},
        ]
        bad_files = [
            {"relpath": "Wiki/L0_超纲词/a.md", "errors": ["entry_1_missing_translation", "entry_1_missing_source"]},
            {"relpath": "Wiki/L0_超纲词/b.md", "errors": ["missing_target_word"]},
            {"relpath": "Wiki/L0_超纲词/c.md", "errors": ["entry_1_missing_source_url"]},
        ]
        out = mod.select_metadata_batch(scope_items, bad_files, limit=2, exclude_relpaths={"Wiki/L0_超纲词/c.md"})
        self.assertEqual([item["relpath"] for item in out], ["Wiki/L0_超纲词/a.md"])

    def test_builds_translated_raw_hits_from_fetchers(self):
        mod = load_module("global_corpus_batch_fill.py", "global_corpus_batch_fill")
        item = {
            "scope_id": "g-0001",
            "relpath": "Wiki/L0_超纲词/a.md",
            "word": "induct",
            "required_count": 2,
        }

        def fake_fetch_oxford(word: str):
            self.assertEqual(word, "induct")
            return [
                {"sentence": "He was inducted into the US Army in July.", "tag": "[例]", "source": "Oxford", "url": "https://oxford/induct"},
                {"sentence": "They were inducted into the skills of magic.", "tag": "[例]", "source": "Oxford", "url": "https://oxford/induct"},
            ]

        def fake_fetch_mw(word: str):
            return []

        def fake_fetch_cambridge(word: str):
            return []

        out = mod.build_raw_hits_for_item(
            item,
            translator=lambda s: f"中译:{s}",
            fetchers=[fake_fetch_oxford, fake_fetch_mw, fake_fetch_cambridge],
        )
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["scope_id"], "g-0001")
        self.assertEqual(out[0]["relpath"], "Wiki/L0_超纲词/a.md")
        self.assertEqual(out[0]["translation"], "中译:He was inducted into the US Army in July.")

    def test_builds_raw_hits_when_required_count_missing(self):
        mod = load_module("global_corpus_batch_fill.py", "global_corpus_batch_fill")
        item = {
            "scope_id": "g-0002",
            "relpath": "Wiki/L0_基础词/b.md",
            "word": "specific",
            "word_freq": "基础词",
        }

        def fake_fetch(word: str):
            return [
                {"sentence": "The money was collected for a specific purpose.", "tag": "[例]", "source": "Oxford", "url": "https://oxford/specific"},
                {"sentence": "I gave you specific instructions.", "tag": "[例]", "source": "Oxford", "url": "https://oxford/specific"},
                {"sentence": "These values are culturally specific, not naturally given.", "tag": "[例]", "source": "Oxford", "url": "https://oxford/specific"},
            ]

        out = mod.build_raw_hits_for_item(
            item,
            translator=lambda s: f"中译:{s}",
            fetchers=[fake_fetch],
        )
        self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main()
