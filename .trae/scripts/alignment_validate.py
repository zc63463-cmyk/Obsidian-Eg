#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一验收格式对齐与语料修复结果。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from alignment_scan import detect_structure_issues, scan_corpus_issues


REPO = Path("/workspace/Obsidian-Eg")
SCOPE_JSON = Path("/data/user/work/alignment_scope.json")
OUT_JSON = Path("/data/user/work/alignment_validate_report.json")


def validate_text(text: str, word: str, word_freq: str) -> List[str]:
    import re

    pos_m = re.search(r"^pos:\s*(.+?)\s*$", text, flags=re.M)
    field_m = re.search(r"^semantic_field:\s*(.+?)\s*$", text, flags=re.M)
    pos = (pos_m.group(1).strip() if pos_m else "").strip('"').strip("'")
    semantic_field = (field_m.group(1).strip() if field_m else "").strip('"').strip("'")
    return detect_structure_issues(text) + scan_corpus_issues(text, word, word_freq, pos, semantic_field)


def main() -> None:
    scope = json.loads(SCOPE_JSON.read_text(encoding="utf-8"))
    bad_files: List[Dict[str, object]] = []
    for item in scope["items"]:
        relpath = item["relpath"]
        p = REPO / relpath
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        errors = validate_text(text, p.stem, item.get("word_freq", ""))
        if errors:
            bad_files.append({"relpath": relpath, "errors": errors})
    payload = {
        "files_total": len(scope["items"]),
        "bad_count": len(bad_files),
        "bad_files": bad_files,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"bad_count={len(bad_files)}")
    print(f"out={OUT_JSON}")


if __name__ == "__main__":
    main()
