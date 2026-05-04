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

import alignment_scope as base_scope
from global_corpus_workdir import work_path


ALIGNMENT_SCOPE_JSON = work_path("alignment_scope.json")
OUT_JSON = work_path("global_corpus_scope.json")


def required_count(word_freq: str) -> int:
    return 3 if word_freq in {"必备词", "基础词"} else 2


def build_global_scope_items(relpaths: List[str], freq_map: Dict[str, str]) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    for idx, relpath in enumerate(relpaths, 1):
        word_freq = freq_map[relpath]
        items.append(
            {
                "scope_id": f"g-{idx:04d}",
                "relpath": relpath,
                "word": Path(relpath).stem,
                "word_freq": word_freq,
                "required_count": required_count(word_freq),
            }
        )
    return items


def main() -> None:
    if ALIGNMENT_SCOPE_JSON.exists():
        payload = json.loads(ALIGNMENT_SCOPE_JSON.read_text(encoding="utf-8"))
    else:
        relpaths = base_scope.collect_all_vocab_relpaths()
        freq_map = base_scope.load_word_freq_map(relpaths)
        payload = {
            "items": [
                {
                    "relpath": relpath,
                    "word": Path(relpath).stem,
                    "word_freq": freq_map.get(relpath, ""),
                }
                for relpath in relpaths
            ]
        }
    relpaths = [item["relpath"] for item in payload["items"]]
    freq_map = {item["relpath"]: item["word_freq"] for item in payload["items"]}
    items = build_global_scope_items(relpaths, freq_map)
    OUT_JSON.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"scope_items={len(items)}")


if __name__ == "__main__":
    main()
