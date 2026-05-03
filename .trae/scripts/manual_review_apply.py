#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 manual_review_candidates.json 回写问题词条的语料区块。

输出：
- /data/user/work/manual_review_apply_stats.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO = Path("/workspace/Obsidian-Eg")
CANDIDATES = Path("/data/user/work/manual_review_candidates.json")
APPLY_STATS = Path("/data/user/work/manual_review_apply_stats.json")


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(text)


def corpus_block_span(text: str) -> Optional[Tuple[int, int, str]]:
    m = re.search(r"(?m)^(>[ \t]*\[!example\]-[ \t]*语料(?:[ \t].*)?)\r?\n", text)
    if not m:
        return None
    header = m.group(1)
    start = m.start()
    pos = m.end()
    while pos < len(text):
        line_end = text.find("\n", pos)
        if line_end == -1:
            line_end = len(text)
        line = text[pos:line_end]
        if not line.startswith(">"):
            break
        pos = line_end + 1
    return start, pos, header


def build_block(header: str, entries: List[Dict[str, str]]) -> str:
    lines = [header]
    for entry in entries:
        sent = entry["sentence"].strip()
        tag = entry["tag"].strip() or "[例]"
        lines.append(f"> - {sent} `{tag}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    obj = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    items: List[Dict[str, object]] = obj["items"]
    target_group = sys.argv[1] if len(sys.argv) > 1 else "all"

    changed_files = []
    skipped_files = []
    changed_entry_count = 0
    unresolved_files = []

    for item in items:
        if target_group != "all" and item.get("group") != target_group:
            continue
        relpath = item["relpath"]
        final_entries: List[Dict[str, str]] = item["final_entries"]
        if not final_entries:
            skipped_files.append(relpath)
            continue

        path = REPO / relpath
        text = read_text(path)
        span = corpus_block_span(text)
        if not span:
            skipped_files.append(relpath)
            continue
        start, end, header = span
        old_block = text[start:end]
        new_block = build_block(header, final_entries)
        if old_block == new_block:
            if item.get("unresolved"):
                unresolved_files.append(relpath)
            continue

        new_text = text[:start] + new_block + text[end:]
        write_text(path, new_text)
        changed_files.append(relpath)
        changed_entry_count += len(item["replacements"])
        if item.get("unresolved"):
            unresolved_files.append(relpath)

    APPLY_STATS.write_text(
        json.dumps(
            {
                "changed_files": changed_files,
                "changed_file_count": len(changed_files),
                "changed_entry_count": changed_entry_count,
                "skipped_files": skipped_files,
                "unresolved_files": unresolved_files,
                "unresolved_file_count": len(set(unresolved_files)),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"changed_files={len(changed_files)}")
    print(f"changed_entries={changed_entry_count}")
    print(f"unresolved_files={len(set(unresolved_files))}")
    print(f"stats={APPLY_STATS}")


if __name__ == "__main__":
    main()
