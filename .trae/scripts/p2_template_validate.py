#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from alignment_scan import scan_corpus_issues


REPO = Path("/workspace/Obsidian-Eg")
SCOPE_JSON = Path("/data/user/work/p2_template_corpus_scope.json")
OUT_JSON = Path("/data/user/work/p2_template_validate_report.json")


def validate_text(text: str, word: str, word_freq: str) -> List[str]:
    import re

    pos_m = re.search(r"^pos:\s*(.+?)\s*$", text, flags=re.M)
    field_m = re.search(r"^semantic_field:\s*(.+?)\s*$", text, flags=re.M)
    pos = (pos_m.group(1).strip() if pos_m else "").strip('"').strip("'")
    field = (field_m.group(1).strip() if field_m else "").strip('"').strip("'")
    return scan_corpus_issues(text, word, word_freq, pos, field)


def main() -> None:
    scope = json.loads(SCOPE_JSON.read_text(encoding="utf-8"))["items"]
    bad_files: List[Dict[str, object]] = []
    for item in scope:
        p = REPO / item["relpath"]
        text = p.read_text(encoding="utf-8")
        errors = validate_text(text, item["word"], item["word_freq"])
        filtered = [e for e in errors if e.startswith("entry_") or e == "insufficient_corpus_count"]
        if filtered:
            bad_files.append({"relpath": item["relpath"], "errors": filtered})
    OUT_JSON.write_text(
        json.dumps({"files_total": len(scope), "bad_count": len(bad_files), "bad_files": bad_files}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"bad_count={len(bad_files)}")


if __name__ == "__main__":
    main()
