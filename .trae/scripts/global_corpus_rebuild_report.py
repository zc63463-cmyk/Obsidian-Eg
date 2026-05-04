#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from global_corpus_workdir import WORK_DIR


WORK = WORK_DIR
OUT_MD = Path("/workspace/Obsidian-Eg/.trae/reports/全量语料重构报告.md")


def load_json(name: str):
    path = WORK / name
    if not path.exists():
        return {"items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    scope = load_json("global_corpus_scope.json")
    inventory = load_json("global_corpus_inventory.json")
    candidates = load_json("global_corpus_candidates.json")
    apply_stats = load_json("global_corpus_apply_stats.json")
    validate = load_json("global_corpus_validate_report.json")
    queue = load_json("global_corpus_browser_queue.json")
    unresolved = load_json("global_corpus_unresolved.json")
    inventory_counter = Counter(item.get("status", "") for item in inventory.get("items", []))
    blocked_counter = Counter()
    for item in candidates.get("items", []):
        blocked_counter.update(item.get("blocked_reasons", []))
    error_counts = validate.get("error_counts", {})
    lines = [
        "# 全量语料重构报告",
        "",
        f"- 全量词条数：{len(scope.get('items', []))}",
        f"- inventory entry 数：{len(inventory.get('items', []))}",
        f"- verified_keep 数：{inventory_counter.get('verified_keep', 0)}",
        f"- candidate_preserve_backfill 数：{inventory_counter.get('candidate_preserve_backfill', 0)}",
        f"- external_refetch 数：{inventory_counter.get('external_refetch', 0)}",
        f"- template_refetch 数：{inventory_counter.get('template_refetch', 0)}",
        f"- unverifiable_exam_refetch 数：{inventory_counter.get('unverifiable_exam_refetch', 0)}",
        f"- changed_files：{apply_stats.get('changed_file_count', 0)}",
        f"- identical_block_files：{apply_stats.get('identical_block_file_count', 0)}",
        f"- strict_not_ready_files：{apply_stats.get('strict_not_ready_file_count', 0)}",
        f"- missing_callout_files：{apply_stats.get('missing_callout_file_count', 0)}",
        f"- 浏览器队列数：{len(queue.get('items', []))}",
        f"- unresolved file 数：{len(unresolved.get('items', []))}",
        f"- 当前 bad_count：{validate.get('bad_count', '')}",
        "",
        "## Top Blocked Reasons",
    ]
    for reason, count in blocked_counter.most_common(10):
        lines.append(f"- {reason}: {count}")
    lines.extend([
        "",
        "## Top Validate Reasons",
    ])
    for reason, count in sorted(error_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]:
        lines.append(f"- {reason}: {count}")
    lines.extend([
        "",
        "## Apply Stats",
        f"- inventory_driven_noop_files：{apply_stats.get('inventory_driven_noop_file_count', 0)}",
        f"- changed_entries：{apply_stats.get('changed_entries', 0)}",
        f"- unresolved_file_count：{apply_stats.get('unresolved_file_count', 0)}",
    ])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report={OUT_MD}")


if __name__ == "__main__":
    main()
