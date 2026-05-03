#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 manual_review_candidates_39_41.json 回写第39-41批人工复核词条的语料区块。

仅对达到严格准入条件的词条写回：
- final_entries 非空
- unresolved = false
- final_entries 数量达到 required_count

输出：
- /data/user/work/manual_review_apply_stats_39_41.json
- /data/user/work/manual_review_unresolved_39_41.json
- /data/user/work/manual_review_unresolved_39_41.txt
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO = Path("/workspace/Obsidian-Eg")
CANDIDATES = Path("/data/user/work/manual_review_candidates_39_41.json")
APPLY_STATS = Path("/data/user/work/manual_review_apply_stats_39_41.json")
UNRESOLVED_JSON = Path("/data/user/work/manual_review_unresolved_39_41.json")
UNRESOLVED_TXT = Path("/data/user/work/manual_review_unresolved_39_41.txt")


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


def strict_ready(item: Dict[str, object]) -> bool:
    final_entries: List[Dict[str, str]] = item.get("final_entries", [])  # type: ignore[assignment]
    required_count = int(item.get("required_count", 2))
    if item.get("unresolved"):
        return False
    if len(final_entries) < required_count:
        return False
    for entry in final_entries:
        if entry.get("source") in {"Unknown", "NoSource", ""}:
            return False
    return True


def main() -> None:
    obj = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    items: List[Dict[str, object]] = obj["items"]

    changed_files = []
    skipped_files = []
    unresolved_items = []
    changed_entry_count = 0

    for item in items:
        relpath = str(item["relpath"])
        if not strict_ready(item):
            skipped_files.append(relpath)
            unresolved_items.append(
                {
                    "word": item["word"],
                    "relpath": relpath,
                    "required_count": item["required_count"],
                    "current_count": len(item.get("final_entries", [])),
                    "reasons": item.get("unresolved_reasons", []),
                }
            )
            continue

        final_entries: List[Dict[str, str]] = item["final_entries"]  # type: ignore[assignment]
        path = REPO / relpath
        text = read_text(path)
        span = corpus_block_span(text)
        if not span:
            skipped_files.append(relpath)
            unresolved_items.append(
                {
                    "word": item["word"],
                    "relpath": relpath,
                    "required_count": item["required_count"],
                    "current_count": len(final_entries),
                    "reasons": ["missing_corpus_callout"],
                }
            )
            continue

        start, end, header = span
        old_block = text[start:end]
        new_block = build_block(header, final_entries)
        if old_block != new_block:
            new_text = text[:start] + new_block + text[end:]
            write_text(path, new_text)
            changed_files.append(relpath)
            changed_entry_count += len(item.get("replacements", []))

    APPLY_STATS.write_text(
        json.dumps(
            {
                "changed_files": changed_files,
                "changed_file_count": len(changed_files),
                "changed_entry_count": changed_entry_count,
                "skipped_files": skipped_files,
                "skipped_file_count": len(skipped_files),
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
    UNRESOLVED_TXT.write_text(
        "\n".join(
            f"{item['word']}\t{item['relpath']}\t{','.join(item['reasons']) or 'unresolved'}"
            for item in unresolved_items
        )
        + ("\n" if unresolved_items else ""),
        encoding="utf-8",
    )

    print(f"changed_files={len(changed_files)}")
    print(f"changed_entries={changed_entry_count}")
    print(f"unresolved_files={len(unresolved_items)}")
    print(f"stats={APPLY_STATS}")


if __name__ == "__main__":
    main()
