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


class P2TemplateFetchTest(unittest.TestCase):
    def test_keeps_only_non_template_existing_entries(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        text = """
## 真题/语料关联

> [!example]- 语料
> - The report highlights the importance of ability in the final decision. `[例]`
> - Students need the ability to analyze data from different sources. `[例]`
>   - 中译：学生需要具备分析不同来源数据的能力。
>   - 来源：Cambridge | https://dictionary.cambridge.org/example/english/ability
> - She showed remarkable ability in solving complex design problems. `[例]`
>   - 中译：她在解决复杂设计问题时展现出非凡能力。
>   - 来源：Oxford | https://www.oxfordlearnersdictionaries.com/definition/english/ability
"""
        kept = mod.extract_existing_good_entries(text, "ability", "n.", "抽象关系")
        self.assertEqual(len(kept), 2)
        self.assertTrue(all("importance of ability" not in item["sentence"] for item in kept))

    def test_existing_entries_also_reject_chinese_and_mcq_residue(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        text = """
## 真题/语料关联

> [!example]- 语料
> - 第15页，共15页 2024 考研英语真题解析. `[真题]`
>   - 中译：第15页，共15页，2024考研英语真题解析。
>   - 来源：Exam | https://example.com/exam-1
> - A. can hardly address a construction crisis B. are believed to come at a wrong time. `[真题]`
>   - 中译：A. 几乎无法解决建设危机 B. 被认为时机不对。
>   - 来源：Exam | https://example.com/exam-2
> - Students need the ability to analyze data from different sources. `[例]`
>   - 中译：学生需要具备分析不同来源数据的能力。
>   - 来源：Cambridge | https://dictionary.cambridge.org/example/english/ability
"""
        kept = mod.extract_existing_good_entries(text, "ability", "n.", "抽象关系")
        self.assertEqual([item["sentence"] for item in kept], [
            "Students need the ability to analyze data from different sources."
        ])

    def test_existing_unannotated_entries_are_not_reused_for_new_annotated_mode(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        text = """
## 真题/语料关联

> [!example]- 语料
> - Students need the ability to analyze data from different sources. `[例]`
> - She showed remarkable ability in solving complex design problems. `[例]`
> - The course develops students' ability to evaluate evidence critically. `[例]`
"""
        kept = mod.extract_existing_good_entries(text, "ability", "n.", "抽象关系")
        self.assertEqual(kept, [])

    def test_existing_annotated_entries_can_be_reused(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        text = """
## 真题/语料关联

> [!example]- 语料
> - Students need the ability to analyze data from different sources. `[例]`
>   - 中译：学生需要具备分析不同来源数据的能力。
>   - 来源：Cambridge | https://dictionary.cambridge.org/example/english/ability
"""
        kept = mod.extract_existing_good_entries(text, "ability", "n.", "抽象关系")
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["source"], "Cambridge")
        self.assertEqual(kept[0]["url"], "https://dictionary.cambridge.org/example/english/ability")
        self.assertEqual(kept[0]["translation"], "学生需要具备分析不同来源数据的能力。")

    def test_existing_entries_reject_spaced_ocr_noise_even_if_word_matches(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        text = """
## 真题/语料关联

> [!example]- 语料
> - In y o u r e s s a y , y o u s h o u ld describe how a broken rib affects breathing. `[真题]`
>   - 中译：在你的文章中，你应描述断裂的肋骨如何影响呼吸。
>   - 来源：Exam | https://example.com/exam-rib
> - He cooked rib of lamb for Sunday lunch. `[例]`
>   - 中译：他做了羊排作为周日午餐。
>   - 来源：Cambridge | https://dictionary.cambridge.org/example/english/rib
> - She elbowed me in the ribs before I could say anything. `[例]`
>   - 中译：我还没来得及开口，她就用手肘顶了我的肋部一下。
>   - 来源：Oxford | https://www.oxfordlearnersdictionaries.com/definition/english/rib
"""
        kept = mod.extract_existing_good_entries(text, "rib", "n.", "人体动作")
        self.assertEqual([item["sentence"] for item in kept], [
            "He cooked rib of lamb for Sunday lunch.",
            "She elbowed me in the ribs before I could say anything.",
        ])

    def test_build_candidate_pool_prefers_kept_then_static(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        kept = [
            {"sentence": "Students need the ability to analyze data from different sources.", "tag": "[例]", "source": "keep_existing", "url": "local://ability"},
        ]
        static = [
            {"sentence": "She showed remarkable ability in solving complex design problems.", "tag": "[例]", "source": "Cambridge", "url": "https://cambridge/ability"},
            {"sentence": "The report highlights the importance of ability in the final decision.", "tag": "[例]", "source": "Cambridge", "url": "https://cambridge/ability2"},
        ]
        final_entries, unresolved = mod.choose_final_entries(kept, static, "ability", "必备词", "n.", "抽象关系")
        self.assertEqual(len(final_entries), 2)
        self.assertFalse(any("importance of ability" in item["sentence"] for item in final_entries))
        self.assertTrue(unresolved)

    def test_rejects_ocr_spaced_exam_candidate(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        bad = {
            "sentence": "C o m in g a t a tim e o f fre s h in c e n tiv e s fro m th e U K g o v e rn m e n t.",
            "tag": "[真题]",
            "source": "exam",
            "url": "https://example.com/exam",
        }
        self.assertFalse(mod.candidate_allowed(bad, "lie", "v.", "抽象关系"))

    def test_rejects_candidate_with_chinese_or_mcq_residue(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        bad_cn = {
            "sentence": "第15页，共15页 2024 考研英语真题解析.",
            "tag": "[真题]",
            "source": "exam",
            "url": "https://example.com/exam",
        }
        bad_mcq = {
            "sentence": "A. can hardly address a construction crisis B. are believed to come at a wrong time C. seem misleading.",
            "tag": "[真题]",
            "source": "exam",
            "url": "https://example.com/exam2",
        }
        self.assertFalse(mod.candidate_allowed(bad_cn, "rib", "n.", "人体动作"))
        self.assertFalse(mod.candidate_allowed(bad_mcq, "arise", "v.", "抽象关系"))

    def test_candidate_allowed_accepts_alias_spelling_match(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        item = {
            "sentence": "Pediatrics has seen major advances in neonatal care.",
            "tag": "[例]",
            "source": "Cambridge",
            "url": "https://dictionary.cambridge.org/example/english/pediatrics",
        }
        self.assertTrue(mod.candidate_allowed(item, "paediatrics", "n.", "社会专业"))

    def test_merge_browser_hits_for_item_filters_and_returns_verified_hits(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        browser_hits = [
            {
                "scope_id": "p2-4477",
                "relpath": "Wiki/L0_超纲词/paediatrics.md",
                "word": "paediatrics",
                "sentence": "Pediatrics has seen major advances in neonatal care.",
                "tag": "[例]",
                "source": "Browser",
                "url": "https://dictionary.cambridge.org/example/english/pediatrics",
                "acquisition_mode": "browser",
            },
            {
                "scope_id": "p2-4477",
                "relpath": "Wiki/L0_超纲词/paediatrics.md",
                "word": "paediatrics",
                "sentence": "The report highlights the importance of paediatrics in the final decision.",
                "tag": "[例]",
                "source": "Browser",
                "url": "https://bad.example/template",
                "acquisition_mode": "browser",
            },
        ]
        merged = mod.merge_browser_hits_for_item(
            browser_hits,
            scope_id="p2-4477",
            relpath="Wiki/L0_超纲词/paediatrics.md",
            word="paediatrics",
            pos="n.",
            semantic_field="社会专业",
        )
        self.assertEqual([item["sentence"] for item in merged], [
            "Pediatrics has seen major advances in neonatal care."
        ])

    def test_merge_browser_hits_can_match_by_relpath_when_scope_id_changes(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        browser_hits = [
            {
                "scope_id": "g-old",
                "relpath": "Wiki/L0_单词集合/specialist.md",
                "word": "specialist",
                "sentence": "She's a specialist in modern French literature.",
                "tag": "[例]",
                "source": "Oxford",
                "url": "https://www.oxfordlearnersdictionaries.com/definition/english/specialist_1",
                "translation": "她是现代法国文学方面的专家。",
                "acquisition_mode": "browser",
            }
        ]
        merged = mod.merge_browser_hits_for_item(
            browser_hits,
            scope_id="g-new",
            relpath="Wiki/L0_单词集合/specialist.md",
            word="specialist",
            pos="n.",
            semantic_field="社会专业",
        )
        self.assertEqual([item["sentence"] for item in merged], [
            "She's a specialist in modern French literature."
        ])

    def test_browser_queue_created_when_required_count_not_met(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        queue_item = mod.make_browser_queue_item(
            scope_id="p2-0001",
            relpath="Wiki/L0_单词集合/ability.md",
            word="ability",
            required_count=3,
        )
        self.assertEqual(queue_item["scope_id"], "p2-0001")
        self.assertEqual(queue_item["word"], "ability")
        self.assertEqual(queue_item["required_count"], 3)
        self.assertIn("https://dictionary.cambridge.org/dictionary/english/ability", queue_item["urls"][0])

    def test_browser_queue_includes_alias_urls_for_british_spelling_words(self):
        mod = load_module("p2_template_fetch.py", "p2_template_fetch")
        queue_item = mod.make_browser_queue_item(
            scope_id="p2-4477",
            relpath="Wiki/L0_超纲词/paediatrics.md",
            word="paediatrics",
            required_count=2,
        )
        urls = queue_item["urls"]
        self.assertIn("https://dictionary.cambridge.org/dictionary/english/paediatrics", urls)
        self.assertIn("https://dictionary.cambridge.org/dictionary/english/pediatrics", urls)


if __name__ == "__main__":
    unittest.main()
