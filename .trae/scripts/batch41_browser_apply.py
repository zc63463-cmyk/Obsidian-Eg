#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 browser fallback 命中的结构化结果合并回第41批词条。

输入：
- /data/user/work/batch41_browser_hits.json

输出：
- /data/user/work/batch41_browser_apply_stats.json

说明：
- 本脚本不直接驱动浏览器；
- 只消费已结构化的 browser hits；
- 仅修改 `> [!example]- 语料`。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from batch41_validate import keep_if_contains_word, looks_like_full_sentence, strip_tag


REPO = Path("/workspace/Obsidian-Eg")
LIST_FILE = REPO / ".trae" / "batches" / "batch41_files.txt"
HITS_FILE = Path("/data/user/work/batch41_browser_hits.json")
STATS_FILE = Path("/data/user/work/batch41_browser_apply_stats.json")


def read_text(p: Path) -> str:
    with p.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def write_text(p: Path, text: str) -> None:
    with p.open("w", encoding="utf-8", newline="") as f:
        f.write(text)


def normalize_sentence(s: str) -> str:
    s = re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()
    s = s.strip('"\'“”‘’')
    s = s.rstrip('"\'“”‘’').strip()
    if not s:
        return ""
    if s[0].islower():
        s = s[0].upper() + s[1:]
    if s[-1] not in ".?!":
        s += "."
    return s


def sent_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def corpus_block_span(text: str) -> Optional[Tuple[int, int]]:
    m = re.search(r"(?m)^>[ \t]*\[!example\]-[ \t]*语料(?:[ \t].*)?\r?\n", text)
    if not m:
        return None
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
    return start, pos


def parse_bullets(block: str) -> List[str]:
    out: List[str] = []
    for ln in block.splitlines():
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if m:
            out.append(m.group(1).rstrip())
    return out


def load_hits() -> Dict[str, List[Dict[str, str]]]:
    if not HITS_FILE.exists():
        return {}
    obj = json.loads(HITS_FILE.read_text(encoding="utf-8"))
    groups: Dict[str, List[Dict[str, str]]] = {}
    allowed = {ln.strip() for ln in LIST_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()}
    for item in obj.get("items", []):
        relpath = str(item.get("relpath", "")).strip()
        if not relpath or relpath not in allowed:
            continue
        groups.setdefault(relpath, []).append(item)
    return groups


def keep_existing(word: str, bullets: List[str]) -> Tuple[List[str], set[str]]:
    kept: List[str] = []
    seen: set[str] = set()
    for raw in bullets:
        sentence, tag = strip_tag(raw)
        sentence = normalize_sentence(sentence)
        if not sentence:
            continue
        if not keep_if_contains_word(word, sentence):
            continue
        if not looks_like_full_sentence(sentence):
            continue
        key = sent_key(sentence)
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(f"{sentence} `{tag or '[例]'}`")
    return kept, seen


def merge_hits(relpath: str, items: List[Dict[str, str]]) -> Tuple[bool, int]:
    path = REPO / relpath
    word = Path(relpath).stem
    text = read_text(path)
    span = corpus_block_span(text)
    if not span:
        return False, 0
    start, end = span
    block = text[start:end]
    kept, seen = keep_existing(word, parse_bullets(block))

    added_count = 0
    for item in items:
        sentence = normalize_sentence(str(item.get("sentence", "")))
        tag = str(item.get("tag", "[例]")).strip() or "[例]"
        if not sentence:
            continue
        if not keep_if_contains_word(word, sentence):
            continue
        if not looks_like_full_sentence(sentence):
            continue
        key = sent_key(sentence)
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(f"{sentence} `{tag}`")
        added_count += 1

    lines = block.splitlines()
    out_lines: List[str] = []
    header_done = False
    for ln in lines:
        if not header_done:
            out_lines.append(ln)
            if re.match(r"^>[ \t]*\[!example\]-[ \t]*语料", ln):
                header_done = True
            continue
        if re.match(r"^>\s*-\s+", ln):
            continue
        out_lines.append(ln)
    for bullet in kept:
        out_lines.append(f"> - {bullet}")

    new_block = "\n".join(out_lines) + ("\n" if block.endswith("\n") else "")
    new_text = text[:start] + new_block + text[end:]
    changed = new_text != text
    if changed:
        write_text(path, new_text)
    return changed, added_count


def main() -> None:
    grouped = load_hits()
    stats = {"files_touched": 0, "sentences_added": 0}
    for relpath, items in grouped.items():
        changed, added = merge_hits(relpath, items)
        if changed:
            stats["files_touched"] += 1
        stats["sentences_added"] += added
    STATS_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
