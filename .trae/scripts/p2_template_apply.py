#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO = Path("/workspace/Obsidian-Eg")
CANDIDATES = Path("/data/user/work/p2_template_candidates.json")
APPLY_STATS = Path("/data/user/work/p2_template_apply_stats.json")
UNRESOLVED_JSON = Path("/data/user/work/p2_template_unresolved.json")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


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
        sent = re.sub(r"\s+([.?!])$", r"\1", entry["sentence"].strip())
        tag = entry.get("tag", "[例]").strip() or "[例]"
        translation = entry.get("translation", "").strip()
        source = entry.get("source", "").strip()
        url = entry.get("url", "").strip()
        lines.append(f"> - {sent} `{tag}`")
        if translation:
            lines.append(f">   - 中译：{translation}")
        if source and url:
            lines.append(f">   - 来源：{source} | {url}")
    return "\n".join(lines) + "\n"


def strict_ready(item: Dict[str, object]) -> bool:
    final_entries: List[Dict[str, str]] = item.get("final_entries", [])  # type: ignore[assignment]
    required_count = int(item.get("required_count", 2))
    if item.get("unresolved"):
        return False
    if len(final_entries) < required_count:
        return False
    for entry in final_entries:
        if entry.get("source") in {"Unknown", "NoSource", "", "Browser"}:
            return False
        if not entry.get("url"):
            return False
        if not entry.get("translation"):
            return False
    return True


def main() -> None:
    obj = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    items: List[Dict[str, object]] = obj["items"]
    changed_files = []
    unresolved_items = []

    for item in items:
        relpath = str(item["relpath"])
        if not strict_ready(item):
            unresolved_items.append(
                {
                    "scope_id": item.get("scope_id"),
                    "word": item["word"],
                    "relpath": relpath,
                    "required_count": item["required_count"],
                    "current_count": len(item.get("final_entries", [])),
                    "reasons": item.get("unresolved_reasons", []),
                }
            )
            continue

        path = REPO / relpath
        text = read_text(path)
        span = corpus_block_span(text)
        if not span:
            unresolved_items.append(
                {
                    "scope_id": item.get("scope_id"),
                    "word": item["word"],
                    "relpath": relpath,
                    "required_count": item["required_count"],
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

    APPLY_STATS.write_text(
        json.dumps(
            {
                "changed_files": changed_files,
                "changed_file_count": len(changed_files),
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
