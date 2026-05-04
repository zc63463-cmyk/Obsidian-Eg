#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_alignment_rules import normalize_sentence


RAW_JSON = Path("/data/user/work/p2_template_browser_hits_raw.json")
OUT_JSON = Path("/data/user/work/p2_template_browser_hits.json")


def normalize_browser_hit(hit: Dict[str, str]) -> Optional[Dict[str, str]]:
    if not hit.get("url"):
        return None
    sentence = normalize_sentence(hit.get("sentence", ""))
    if not sentence:
        return None
    return {
        "scope_id": str(hit.get("scope_id", "")),
        "relpath": str(hit.get("relpath", "")),
        "word": str(hit.get("word", "")),
        "sentence": sentence if sentence[-1] in ".?!" else sentence + ".",
        "tag": str(hit.get("tag", "[例]") or "[例]"),
        "source": str(hit.get("source", "Browser") or "Browser"),
        "url": str(hit.get("url", "")),
        "acquisition_mode": "browser",
    }


def main() -> None:
    if not RAW_JSON.exists():
        OUT_JSON.write_text(json.dumps({"items": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("normalized_hits=0")
        return
    raw = json.loads(RAW_JSON.read_text(encoding="utf-8"))
    items: List[Dict[str, str]] = []
    for hit in raw.get("items", []):
        norm = normalize_browser_hit(hit)
        if norm:
            items.append(norm)
    OUT_JSON.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"normalized_hits={len(items)}")


if __name__ == "__main__":
    main()
