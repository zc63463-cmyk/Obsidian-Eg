#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


from p2_template_apply import build_block, corpus_block_span, read_text, strict_ready, write_text
from global_corpus_workdir import work_path


REPO = Path("/workspace/Obsidian-Eg")
CANDIDATES = work_path("global_corpus_candidates.json")
APPLY_STATS = work_path("global_corpus_apply_stats.json")
UNRESOLVED_JSON = work_path("global_corpus_unresolved.json")


def main() -> None:
    obj = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    items: List[Dict[str, object]] = obj["items"]
    changed_files = []
    identical_block_files = []
    strict_not_ready_files = []
    missing_callout_files = []
    inventory_driven_noop_files = []
    changed_entries = 0
    unresolved_items = []

    for item in items:
        relpath = str(item["relpath"])
        if not strict_ready(item):
            strict_not_ready_files.append(relpath)
            unresolved_items.append(
                {
                    "scope_id": item.get("scope_id"),
                    "word": item["word"],
                    "relpath": relpath,
                    "required_count": item.get("required_count", 2),
                    "current_count": len(item.get("final_entries", [])),
                    "reasons": item.get("blocked_reasons") or item.get("unresolved_reasons", []),
                }
            )
            continue

        path = REPO / relpath
        text = read_text(path)
        span = corpus_block_span(text)
        if not span:
            missing_callout_files.append(relpath)
            unresolved_items.append(
                {
                    "scope_id": item.get("scope_id"),
                    "word": item["word"],
                    "relpath": relpath,
                    "required_count": item.get("required_count", 2),
                    "current_count": len(item.get("final_entries", [])),
                    "reasons": ["missing_corpus_callout"],
                }
            )
            continue

        start, end, header = span
        new_block = build_block(header, item["final_entries"])  # type: ignore[arg-type]
        if text[start:end] != new_block:
            write_text(path, text[:start] + new_block + text[end:])
            changed_files.append(relpath)
            changed_entries += len(item.get("final_entries", []))
        elif item.get("inventory_actionable_count", 0):
            identical_block_files.append(relpath)
            inventory_driven_noop_files.append(relpath)

    APPLY_STATS.write_text(
        json.dumps(
            {
                "changed_files": changed_files,
                "changed_file_count": len(changed_files),
                "identical_block_files": identical_block_files,
                "identical_block_file_count": len(identical_block_files),
                "strict_not_ready_files": strict_not_ready_files,
                "strict_not_ready_file_count": len(strict_not_ready_files),
                "missing_callout_files": missing_callout_files,
                "missing_callout_file_count": len(missing_callout_files),
                "inventory_driven_noop_files": inventory_driven_noop_files,
                "inventory_driven_noop_file_count": len(inventory_driven_noop_files),
                "changed_entries": changed_entries,
                "unresolved_file_count": len(unresolved_items),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    UNRESOLVED_JSON.write_text(
        json.dumps({"items": unresolved_items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"changed_files={len(changed_files)}")
    print(f"unresolved_files={len(unresolved_items)}")


if __name__ == "__main__":
    main()
