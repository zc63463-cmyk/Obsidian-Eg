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


class AlignmentScopeRulesTest(unittest.TestCase):
    def test_collects_all_vocab_relpaths_from_three_l0_dirs(self):
        mod = load_module("alignment_scope.py", "alignment_scope")
        relpaths = mod.collect_all_vocab_relpaths(
            {
                "Wiki/L0_单词集合/abandon.md",
                "Wiki/L0_单词集合/suggest.md",
                "Wiki/L0_基础词/time.md",
                "Wiki/L0_超纲词/revision.md",
                "Wiki/_系统/_模板-单词笔记.md",
            }
        )
        self.assertEqual(
            relpaths,
            [
                "Wiki/L0_单词集合/abandon.md",
                "Wiki/L0_单词集合/suggest.md",
                "Wiki/L0_基础词/time.md",
                "Wiki/L0_超纲词/revision.md",
            ],
        )

    def test_parse_git_changed_paths_keeps_only_wiki_markdown(self):
        mod = load_module("alignment_scope.py", "alignment_scope")
        raw = "\n".join(
            [
                "Wiki/L0_超纲词/revision.md",
                ".trae/scripts/batch40_apply.py",
                "Wiki/L0_单词集合/abandon.md",
                "README.md",
            ]
        )
        self.assertEqual(
            mod.parse_git_changed_paths(raw),
            [
                "Wiki/L0_单词集合/abandon.md",
                "Wiki/L0_超纲词/revision.md",
            ],
        )

    def test_extracts_wiki_relpaths_from_report_text(self):
        mod = load_module("alignment_scope.py", "alignment_scope")
        report = """
        - `Wiki/L0_超纲词/revision.md`
        - relpath: Wiki/L0_超纲词/low-cost.md
        evidence -> Wiki/L0_单词集合/abandon.md
        """
        self.assertEqual(
            mod.parse_report_relpaths(report),
            [
                "Wiki/L0_单词集合/abandon.md",
                "Wiki/L0_超纲词/low-cost.md",
                "Wiki/L0_超纲词/revision.md",
            ],
        )

    def test_merges_sources_and_tracks_scope_sources(self):
        mod = load_module("alignment_scope.py", "alignment_scope")
        freq_map = {
            "Wiki/L0_超纲词/revision.md": "超纲词",
            "Wiki/L0_超纲词/low-cost.md": "超纲词",
            "Wiki/L0_单词集合/abandon.md": "必备词",
        }
        items = mod.build_scope_items(
            git_paths=["Wiki/L0_超纲词/revision.md", "Wiki/L0_单词集合/abandon.md"],
            batch_paths=["Wiki/L0_超纲词/revision.md", "Wiki/L0_超纲词/low-cost.md"],
            report_paths=["Wiki/L0_超纲词/low-cost.md"],
            freq_map=freq_map,
        )
        self.assertEqual(
            [item["relpath"] for item in items],
            [
                "Wiki/L0_单词集合/abandon.md",
                "Wiki/L0_超纲词/low-cost.md",
                "Wiki/L0_超纲词/revision.md",
            ],
        )
        by_path = {item["relpath"]: item for item in items}
        self.assertEqual(by_path["Wiki/L0_超纲词/revision.md"]["source_scope"], ["batch", "git"])
        self.assertEqual(by_path["Wiki/L0_超纲词/low-cost.md"]["source_scope"], ["batch", "report"])
        self.assertEqual(by_path["Wiki/L0_单词集合/abandon.md"]["word"], "abandon")
        self.assertEqual(by_path["Wiki/L0_单词集合/abandon.md"]["word_freq"], "必备词")


if __name__ == "__main__":
    unittest.main()
