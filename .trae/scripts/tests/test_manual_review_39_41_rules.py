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


class ManualReview3941RulesTest(unittest.TestCase):
    def test_unknown_entries_are_not_allowed_into_final_writeback(self):
        mod = load_module("manual_review_fetch_39_41.py", "manual_review_fetch_39_41")
        item = {
            "required_count": 2,
            "entries": [
                {
                    "sentence": "The policy had unexpected consequences.",
                    "tag": "[例]",
                    "source": "Unknown",
                    "url": "",
                    "issues": ["manual_review_reported"],
                }
            ],
        }
        final_entries, _, unresolved = mod.choose_final_entries_strict(item, [])
        self.assertEqual(final_entries, [])
        self.assertTrue(unresolved)

    def test_known_good_entries_can_be_kept(self):
        mod = load_module("manual_review_fetch_39_41.py", "manual_review_fetch_39_41")
        item = {
            "required_count": 2,
            "entries": [
                {
                    "sentence": "The report was published by a respected think tank.",
                    "tag": "[例]",
                    "source": "Cambridge",
                    "url": "https://dictionary.cambridge.org/example/english/think-tank",
                    "issues": [],
                }
            ],
        }
        candidate_pool = [
            {
                "sentence": "A think-tank released a new policy proposal.",
                "tag": "[例]",
                "source": "Oxford",
                "url": "https://www.oxfordlearnersdictionaries.com/definition/english/think-tank",
                "acquisition_mode": "static",
            }
        ]
        final_entries, _, unresolved = mod.choose_final_entries_strict(item, candidate_pool)
        self.assertEqual(len(final_entries), 2)
        self.assertEqual(final_entries[0]["source"], "Cambridge")
        self.assertEqual(final_entries[1]["source"], "Oxford")
        self.assertFalse(unresolved)

    def test_hyphenated_word_variants_still_count(self):
        mod = load_module("manual_review_fetch_39_41.py", "manual_review_fetch_39_41")
        self.assertTrue(mod.keep_if_contains_word("self-help", "She bought several self help books."))


if __name__ == "__main__":
    unittest.main()
