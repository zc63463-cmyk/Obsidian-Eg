#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第39批范围检查：
- 词条修改集合必须是 `.trae/batches/batch39_files.txt` 的子集
- 允许本批脚本、清单、报告一并改动
- 不要求 100 个词条全部发生修改（已完成项允许跳过）
"""

from pathlib import Path
import subprocess


REPO = Path("/workspace/Obsidian-Eg")
BATCH = REPO / ".trae" / "batches" / "batch39_files.txt"
ALLOWED_AUX = {
    ".trae/batches/batch39_files.txt",
    ".trae/reports/第39批次超纲词801-900_6.5-6.6_处理报告.md",
    ".trae/scripts/batch39_make_list.py",
    ".trae/scripts/batch39_apply.py",
    ".trae/scripts/batch39_online_fill.py",
    ".trae/scripts/batch39_browser_apply.py",
    ".trae/scripts/batch39_validate.py",
    ".trae/scripts/batch39_range_check.py",
    ".trae/scripts/batch39_rebuild_report.py",
    ".trae/scripts/tests/test_batch39_rules.py",
}
CHECKPOINT_FILES = [
    ".trae/scripts/batch39_make_list.py",
    ".trae/scripts/batch39_apply.py",
    ".trae/batches/batch39_files.txt",
]


def classify_out_of_scope_modifications(mods: set[str], batch: set[str]) -> tuple[list[str], list[str]]:
    extra_words = sorted(
        rel for rel in mods
        if rel.startswith("Wiki/") and rel.endswith(".md") and rel not in batch
    )
    extra_other = sorted(
        rel for rel in mods
        if not (rel.startswith("Wiki/") and rel.endswith(".md")) and rel not in ALLOWED_AUX
    )
    return extra_words, extra_other


def task_start_timestamp() -> float:
    stamps = []
    for rel in CHECKPOINT_FILES:
        path = REPO / rel
        if path.exists():
            stamps.append(path.stat().st_mtime)
    if not stamps:
        return 0.0
    return min(stamps) - 1.0


def filter_recent_modifications(mods: set[str]) -> set[str]:
    cutoff = task_start_timestamp()
    recent: set[str] = set()
    for rel in mods:
        path = REPO / rel
        if not path.exists():
            recent.add(rel)
            continue
        if path.stat().st_mtime >= cutoff:
            recent.add(rel)
    return recent


def main() -> None:
    mods = set(
        subprocess.check_output(
            ["git", "-c", "core.quotepath=false", "diff", "--name-only", "--diff-filter=ACMR"],
            cwd=REPO,
        )
        .decode("utf-8")
        .splitlines()
    )
    recent_mods = filter_recent_modifications(mods)
    batch = set([ln.strip() for ln in BATCH.read_text(encoding="utf-8").splitlines() if ln.strip()])
    word_mods = sorted(rel for rel in recent_mods if rel.startswith("Wiki/") and rel.endswith(".md"))
    extra_words, extra_other = classify_out_of_scope_modifications(recent_mods, batch)
    print(f"modified_total={len(mods)} recent_total={len(recent_mods)} modified_words={len(word_mods)} batch={len(batch)}")
    print(f"extra_words={len(extra_words)} extra_other={len(extra_other)}")
    if extra_words:
        print("EXTRA_WORDS:", extra_words[:30])
    if extra_other:
        print("EXTRA_OTHER:", extra_other[:30])
    if extra_words or extra_other:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
