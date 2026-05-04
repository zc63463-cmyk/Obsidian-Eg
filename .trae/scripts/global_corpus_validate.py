#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from alignment_scan import scan_corpus_issues
from global_corpus_workdir import work_path


REPO = Path("/workspace/Obsidian-Eg")
SCOPE_JSON = work_path("global_corpus_scope.json")
OUT_JSON = work_path("global_corpus_validate_report.json")


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
    error_counts: Counter[str] = Counter()
    for item in scope:
        p = REPO / item["relpath"]
        text = p.read_text(encoding="utf-8")
        errors = validate_text(text, item["word"], item["word_freq"])
        filtered = [
            e
            for e in errors
            if e.startswith("entry_") or e in {"insufficient_corpus_count", "duplicate_sentence"}
        ]
        if filtered:
            error_counts.update(filtered)
            bad_files.append({"relpath": item["relpath"], "errors": filtered})
    OUT_JSON.write_text(
        json.dumps(
            {
                "files_total": len(scope),
                "bad_count": len(bad_files),
                "bad_files": bad_files,
                "error_counts": dict(error_counts),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"bad_count={len(bad_files)}")


if __name__ == "__main__":
    main()
