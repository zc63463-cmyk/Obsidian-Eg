#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 manifest + candidates 回刷批次报告，并生成分组汇总报告。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

from manual_review_registry import REPO, get_scopes


MANIFEST = Path("/data/user/work/manual_review_manifest.json")
CANDIDATES = Path("/data/user/work/manual_review_candidates.json")


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def existing_report_title(report_path: Path) -> str:
    if report_path.exists():
        text = read_text(report_path)
        for line in text.splitlines():
            if line.startswith("# "):
                return line
    return f"# {report_path.stem}"


def main() -> None:
    target_group = sys.argv[1] if len(sys.argv) > 1 else "executed"
    summary_report = REPO / ".trae" / "reports" / (
        "人工复核修复汇总报告.md" if target_group == "executed" else f"人工复核修复汇总报告_{target_group}.md"
    )

    manifest_obj = read_json(MANIFEST)
    candidates_obj = read_json(CANDIDATES)
    manifest_items: List[Dict[str, object]] = manifest_obj["items"]  # type: ignore[assignment]
    candidate_items: List[Dict[str, object]] = candidates_obj["items"]  # type: ignore[assignment]

    manifest_items = [item for item in manifest_items if target_group == "all" or item.get("group") == target_group]
    candidate_items = [item for item in candidate_items if target_group == "all" or item.get("group") == target_group]
    manifest_by_rel = {item["relpath"]: item for item in manifest_items}
    candidates_by_rel = {item["relpath"]: item for item in candidate_items}

    summary_rows = []
    total_replacements = 0
    total_unresolved = 0
    total_exam = 0
    total_unknown_after = 0

    scopes = get_scopes(target_group if target_group in {"early", "executed"} else "all")
    for scope in scopes:
        list_file = Path(scope["list_path"])
        report_file = Path(scope["report_path"])
        relpaths = [ln.strip() for ln in read_text(list_file).splitlines() if ln.strip()]
        first_name = Path(relpaths[0]).name if relpaths else ""
        last_name = Path(relpaths[-1]).name if relpaths else ""
        directory = str(Path(relpaths[0]).parent) if relpaths else str(scope["directory"])
        title = existing_report_title(report_file)
        if scope.get("has_existing_report"):
            unknown_before = int(scope.get("unknown_before", 0))
        else:
            unknown_before = sum(
                1
                for item in manifest_items
                if item.get("scope_id") == scope["scope_id"]
                for entry in item["entries"]
                if entry["source"] == "Unknown"
            )

        by_source: Dict[str, int] = {}
        unresolved_words = []
        replacement_rows = []
        batch_replacements = 0
        batch_exam = 0
        batch_unknown_after = 0

        for rel in relpaths:
            cand = candidates_by_rel.get(rel)
            if cand:
                final_entries = cand["final_entries"]
                if cand.get("unresolved"):
                    unresolved_words.append((cand["word"], cand["unresolved_reasons"]))
                for repl in cand["replacements"]:
                    replacement_rows.append(
                        {
                            "word": cand["word"],
                            "old_sentence": repl["old_sentence"],
                            "new_sentence": repl["new_sentence"],
                            "final_tag": repl["final_tag"],
                            "source": repl["source"],
                            "url": repl["url"],
                            "acquisition_mode": "browser" if repl["source"] == "Browser" else "static",
                            "issue_type": ",".join(cand["word_issues"]),
                        }
                    )
                    batch_replacements += 1
                for entry in final_entries:
                    src = entry["source"]
                    by_source[src] = by_source.get(src, 0) + 1
                    if src == "Unknown":
                        batch_unknown_after += 1
                    if entry["tag"] == "[真题]" or entry["tag"].startswith("[考研-"):
                        batch_exam += 1
            else:
                item = manifest_by_rel[rel]
                for entry in item["entries"]:
                    src = entry["source"]
                    by_source[src] = by_source.get(src, 0) + 1
                    if src == "Unknown":
                        batch_unknown_after += 1

        total_replacements += batch_replacements
        total_unresolved += len(unresolved_words)
        total_exam += batch_exam
        total_unknown_after += batch_unknown_after

        lines: List[str] = []
        lines.append(title)
        lines.append("")
        lines.append("## 批次范围")
        lines.append(f"- scope_id: `{scope['scope_id']}`")
        lines.append(f"- 批次号：`{scope['display_batch_id']}`")
        lines.append(f"- 目录：`{directory}/`")
        lines.append("- 排序口径：Python `sorted()` 按文件名")
        lines.append(f"- 文件数：`{len(relpaths)}`")
        if first_name and last_name:
            lines.append(f"- 首尾：`{first_name}` ~ `{last_name}`")
        lines.append("")
        lines.append("## 修复统计")
        lines.append(f"- Unknown_before: {unknown_before}")
        lines.append(f"- Unknown_after: {batch_unknown_after}")
        lines.append(f"- replacements: {batch_replacements}")
        lines.append(f"- exam_tag_entries: {batch_exam}")
        lines.append(f"- unresolved_words: {len(unresolved_words)}")
        lines.append("")
        lines.append("## 最终来源分布")
        for src, count in sorted(by_source.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {src}: {count}")
        lines.append("")
        lines.append("## 剩余人工复核")
        if unresolved_words:
            seen_words = set()
            for word, reasons in unresolved_words:
                if word in seen_words:
                    continue
                seen_words.add(word)
                lines.append(f"- {word}: {', '.join(reasons)}")
        else:
            lines.append("- 无")
        lines.append("")
        lines.append("## 修复证据表")
        lines.append("")
        lines.append("| word | old_sentence | new_sentence | final_tag | source | url | acquisition_mode | issue_type |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for row in replacement_rows:
            lines.append(
                "| {word} | {old_sentence} | {new_sentence} | {final_tag} | {source} | {url} | {acquisition_mode} | {issue_type} |".format(
                    **row
                )
            )
        write_text(report_file, "\n".join(lines) + "\n")

        summary_rows.append(
            {
                "scope_id": scope["scope_id"],
                "batch_id": scope["display_batch_id"],
                "report": report_file.name,
                "unknown_before": unknown_before,
                "unknown_after": batch_unknown_after,
                "replacements": batch_replacements,
                "exam_entries": batch_exam,
                "unresolved": len(unresolved_words),
            }
        )

    lines = [f"# 人工复核修复汇总报告（{target_group}）", ""]
    lines.append("## 汇总统计")
    lines.append(f"- scopes: {len(scopes)}")
    lines.append(f"- replacements: {total_replacements}")
    lines.append(f"- exam_tag_entries: {total_exam}")
    lines.append(f"- unresolved_words: {total_unresolved}")
    lines.append(f"- unknown_after_total: {total_unknown_after}")
    lines.append("")
    lines.append("## 分批结果")
    lines.append("")
    lines.append("| scope_id | batch | report | unknown_before | unknown_after | replacements | exam_entries | unresolved |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|")
    for row in summary_rows:
        lines.append(
            f"| {row['scope_id']} | {row['batch_id']} | {row['report']} | {row['unknown_before']} | {row['unknown_after']} | {row['replacements']} | {row['exam_entries']} | {row['unresolved']} |"
        )
    write_text(summary_report, "\n".join(lines) + "\n")

    print(f"summary={summary_report}")
    print(f"replacements={total_replacements}")
    print(f"unresolved={total_unresolved}")


if __name__ == "__main__":
    main()
