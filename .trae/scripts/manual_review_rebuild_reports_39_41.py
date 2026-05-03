#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建第39-41批人工复核修复汇总报告。

输入：
- /data/user/work/manual_review_candidates_39_41.json
- /data/user/work/manual_review_apply_stats_39_41.json
- /data/user/work/manual_review_unresolved_39_41.json

输出：
- /workspace/Obsidian-Eg/.trae/reports/第39-41批人工复核修复汇总报告.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


REPO = Path("/workspace/Obsidian-Eg")
CANDIDATES = Path("/data/user/work/manual_review_candidates_39_41.json")
APPLY_STATS = Path("/data/user/work/manual_review_apply_stats_39_41.json")
UNRESOLVED = Path("/data/user/work/manual_review_unresolved_39_41.json")
REPORT = REPO / ".trae" / "reports" / "第39-41批人工复核修复汇总报告.md"


def load_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    cand_obj = load_json(CANDIDATES)
    items: List[Dict[str, object]] = cand_obj.get("items", [])  # type: ignore[assignment]
    apply_stats = load_json(APPLY_STATS)
    unresolved_obj = load_json(UNRESOLVED)
    unresolved_items: List[Dict[str, object]] = unresolved_obj.get("items", [])  # type: ignore[assignment]

    by_source: Dict[str, int] = {}
    replacement_rows = []
    exam_entries = 0
    resolved_words = 0

    for item in items:
        if item.get("unresolved"):
            continue
        final_entries: List[Dict[str, str]] = item.get("final_entries", [])  # type: ignore[assignment]
        if not final_entries:
            continue
        resolved_words += 1
        for entry in final_entries:
            source = entry.get("source", "Unknown")
            by_source[source] = by_source.get(source, 0) + 1
            if source.startswith("考研-"):
                exam_entries += 1
        for repl in item.get("replacements", []):
            replacement_rows.append(
                {
                    "word": item["word"],
                    "relpath": item["relpath"],
                    "old_sentence": repl.get("old_sentence", ""),
                    "new_sentence": repl.get("new_sentence", ""),
                    "final_tag": repl.get("final_tag", "[例]"),
                    "source": repl.get("source", ""),
                    "url": repl.get("url", ""),
                    "acquisition_mode": "static",
                    "action_type": repl.get("reason", "replace"),
                }
            )

    lines: List[str] = []
    lines.append("# 第39-41批人工复核修复汇总报告")
    lines.append("")
    lines.append("## 修复范围")
    lines.append("- 范围：仅第39-41批处理报告中“异常/人工复核”区块涉及的词条")
    lines.append(f"- problem_items: {len(items)}")
    lines.append(f"- resolved_words: {resolved_words}")
    lines.append(f"- unresolved_words: {len(unresolved_items)}")
    lines.append("")
    lines.append("## 回写统计")
    lines.append(f"- changed_files: {apply_stats.get('changed_file_count', 0)}")
    lines.append(f"- changed_entries: {apply_stats.get('changed_entry_count', 0)}")
    lines.append(f"- skipped_files: {apply_stats.get('skipped_file_count', 0)}")
    lines.append("")
    lines.append("## 来源分布")
    lines.append(f"- exam_entries: {exam_entries}")
    if by_source:
        for source, count in sorted(by_source.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 未解决词条")
    if unresolved_items:
        for item in unresolved_items:
            reasons = ",".join(item.get("reasons", [])) or "unresolved"
            lines.append(f"- {item['word']}: {reasons}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 替换证据表")
    lines.append("")
    lines.append("| word | relpath | old_sentence | new_sentence | final_tag | source | url | acquisition_mode | action_type |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for row in replacement_rows:
        old_sentence = str(row["old_sentence"]).replace("|", "\\|")
        new_sentence = str(row["new_sentence"]).replace("|", "\\|")
        url = str(row["url"]).replace("|", "\\|")
        lines.append(
            f"| {row['word']} | {row['relpath']} | {old_sentence} | "
            f"{new_sentence} | {row['final_tag']} | {row['source']} | "
            f"{url} | {row['acquisition_mode']} | {row['action_type']} |"
        )

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"resolved_words={resolved_words}")
    print(f"unresolved_words={len(unresolved_items)}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    main()
