#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 scope 内词条做结构归一：
- 删除 mastery
- 删除 掌握/Lx
- 去掉 callout 标题中的 · Lx
- 删除 ## 复习记录 区块
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Tuple


REPO = Path("/workspace/Obsidian-Eg")
SCOPE_JSON = Path("/data/user/work/alignment_scope.json")
OUT_JSON = Path("/data/user/work/alignment_structure_stats.json")


def remove_review_section(text: str) -> Tuple[str, bool]:
    m = re.search(r"(?m)^##\s+复习记录\s*$\n?", text)
    if not m:
        return text, False
    start = m.start()
    rest = text[m.end():]
    m2 = re.search(r"(?m)^##\s+", rest)
    end = m.end() + m2.start() if m2 else len(text)
    return text[:start].rstrip() + "\n\n" + text[end:].lstrip(), True


def normalize_structure(text: str) -> Tuple[str, bool]:
    changed = False
    out = text

    new_out = re.sub(r"(?m)^mastery:\s*.+\n", "", out)
    if new_out != out:
        changed = True
        out = new_out

    new_out = re.sub(r"(?m)^\s*-\s*掌握/L\d+\s*\n", "", out)
    if new_out != out:
        changed = True
        out = new_out

    new_out = re.sub(r"(?m)^(>\s*\[![^\]]+\]-\s*.+?)\s·\sL\d+\s*$", r"\1", out)
    if new_out != out:
        changed = True
        out = new_out

    out2, removed = remove_review_section(out)
    if removed:
        changed = True
        out = out2

    return out, changed


def main() -> None:
    scope = json.loads(SCOPE_JSON.read_text(encoding="utf-8"))
    touched = 0
    for item in scope["items"]:
        relpath = item["relpath"]
        p = REPO / relpath
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        new_text, changed = normalize_structure(text)
        if changed:
            p.write_text(new_text, encoding="utf-8")
            touched += 1
    OUT_JSON.write_text(json.dumps({"touched_files": touched}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"touched_files={touched}")
    print(f"out={OUT_JSON}")


if __name__ == "__main__":
    main()
