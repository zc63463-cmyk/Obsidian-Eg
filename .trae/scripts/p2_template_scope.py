#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List


AUDIT_MANIFEST = Path("/data/user/work/global_audit_manifest.json")
OUT_JSON = Path("/data/user/work/p2_template_corpus_scope.json")


def required_corpus_count(word_freq: str) -> int:
    return 2 if word_freq == "超纲词" else 3


def build_p2_scope(audit_items: List[Dict[str, object]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for idx, item in enumerate(audit_items, 1):
        problems = [str(p) for p in item.get("problems", [])]
        entries = []
        for p in problems:
            m = re.match(r"^entry_(\d+)_template_corpus$", p)
            if m:
                entries.append(int(m.group(1)))
        if not entries:
            continue
        word_freq = str(item.get("word_freq", "") or "")
        out.append(
            {
                "scope_id": f"p2-{idx:04d}",
                "relpath": str(item["relpath"]),
                "word": str(item["word"]),
                "word_freq": word_freq,
                "problem_entries": sorted(entries),
                "required_count": required_corpus_count(word_freq),
                "all_problems": problems,
            }
        )
    return out


def main() -> None:
    audit = json.loads(AUDIT_MANIFEST.read_text(encoding="utf-8"))
    items = build_p2_scope(audit["items"])
    OUT_JSON.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"scope_items={len(items)}")
    print(f"out={OUT_JSON}")


if __name__ == "__main__":
    main()
