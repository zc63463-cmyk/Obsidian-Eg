#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_alignment_rules import parse_corpus_entries
from common_alignment_rules import is_template_corpus
from global_corpus_workdir import work_path


REPO = Path("/workspace/Obsidian-Eg")
SCOPE_JSON = work_path("global_corpus_scope.json")
OUT_JSON = work_path("global_corpus_inventory.json")


def corpus_block(text: str) -> str:
    m = re.search(r"(?m)^>[ \t]*\[!example\]-[ \t]*语料(?:[ \t].*)?\r?\n", text)
    if not m:
        return ""
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
    return text[start:pos]


def classify_entry(entry: Dict[str, str], word: str) -> str:
    translation_present = bool(entry.get("translation", "").strip())
    source_present = bool(entry.get("source_name", "").strip())
    url_present = bool(entry.get("source_url", "").strip())
    raw = entry.get("raw", "")
    tag = entry.get("tag", "").strip()
    if is_template_corpus(entry.get("sentence", ""), word):
        return "template_refetch"
    if translation_present and source_present and url_present:
        return "verified_keep"
    if tag == "[真题]" and not url_present:
        return "unverifiable_exam_refetch"
    if tag in {"[例]", "[真题]"}:
        return "candidate_preserve_backfill"
    return "external_refetch"


def preferred_action_for_status(status: str) -> str:
    if status == "verified_keep":
        return "keep_verified"
    if status == "candidate_preserve_backfill":
        return "preserve_sentence_and_backfill"
    return "external_refetch"


def summarize_file_entries(items: List[Dict[str, object]]) -> Dict[str, int]:
    verified_count = sum(1 for item in items if item["status"] == "verified_keep")
    actionable_count = sum(1 for item in items if item["status"] != "verified_keep")
    missing_url_count = sum(1 for item in items if item.get("needs_url"))
    template_count = sum(1 for item in items if item["status"] == "template_refetch")
    return {
        "verified_count": verified_count,
        "actionable_count": actionable_count,
        "missing_url_count": missing_url_count,
        "template_count": template_count,
    }


def inventory_entries(scope_id: str, relpath: str, word: str, word_freq: str, text: str) -> List[Dict[str, object]]:
    entries = parse_corpus_entries(corpus_block(text))
    out: List[Dict[str, object]] = []
    for idx, entry in enumerate(entries, 1):
        translation_present = bool(entry.get("translation", "").strip())
        source_present = bool(entry.get("source_name", "").strip())
        url_present = bool(entry.get("source_url", "").strip())
        status = classify_entry(entry, word)
        out.append(
            {
                "entry_id": f"{scope_id}:e{idx}",
                "scope_id": scope_id,
                "relpath": relpath,
                "word": word,
                "word_freq": word_freq,
                "entry_index": idx,
                "sentence_key": re.sub(r"[^a-z0-9]+", " ", entry["sentence"].lower()).strip(),
                "original_sentence": entry["sentence"],
                "original_tag": entry["tag"],
                "translation_present": translation_present,
                "source_present": source_present,
                "url_present": url_present,
                "needs_translation": not translation_present,
                "needs_source_name": not source_present,
                "needs_url": not url_present,
                "must_external_refetch": not url_present,
                "status": status,
                "preferred_action": preferred_action_for_status(status),
            }
        )
    return out


def main() -> None:
    payload = json.loads(SCOPE_JSON.read_text(encoding="utf-8"))
    all_items: List[Dict[str, object]] = []
    file_summaries: List[Dict[str, object]] = []
    for item in payload["items"]:
        relpath = item["relpath"]
        text = (REPO / relpath).read_text(encoding="utf-8")
        entries = inventory_entries(
            scope_id=str(item["scope_id"]),
            relpath=relpath,
            word=item["word"],
            word_freq=item["word_freq"],
            text=text,
        )
        all_items.extend(entries)
        file_summaries.append(
            {
                "scope_id": item["scope_id"],
                "relpath": relpath,
                "word": item["word"],
                "word_freq": item["word_freq"],
                **summarize_file_entries(entries),
            }
        )
    OUT_JSON.write_text(
        json.dumps({"items": all_items, "files": file_summaries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"inventory_items={len(all_items)}")


if __name__ == "__main__":
    main()
