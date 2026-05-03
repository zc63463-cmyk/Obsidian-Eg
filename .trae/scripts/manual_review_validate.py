#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨 7 批次校验人工复核修复结果。

输出：
- /data/user/work/manual_review_validate_report.json
- /data/user/work/manual_review_validate_bad.txt
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from manual_review_registry import get_scopes


REPO = Path("/workspace/Obsidian-Eg")
REPORT = Path("/data/user/work/manual_review_validate_report.json")
BAD_TXT = Path("/data/user/work/manual_review_validate_bad.txt")

TAG_RE = re.compile(r"`\[((?:例|真题|考研-[^\]]+))\]`\s*$")
PLACEHOLDER_RE = re.compile(
    r"(please provide an example sentence using the word\b|i learned the word\b|nosource)",
    flags=re.I,
)
AUXILIARIES = {
    "am", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did",
    "have", "has", "had",
    "can", "could", "may", "might", "must", "shall", "should", "will", "would",
}


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def extract_word_freq(text: str) -> str:
    m = re.search(r"^word_freq:\s*(.+?)\s*$", text, flags=re.M)
    return (m.group(1).strip() if m else "").strip('"').strip("'")


def required_corpus_count(word_freq: str) -> int:
    return 2 if word_freq == "超纲词" else 3


def keep_if_contains_word(word: str, s: str) -> bool:
    w = word.lower().strip()
    if not w:
        return False
    last = w[-1]
    consonants = "bcdfghjklmnpqrstvwxyz"
    forms = [w, w + "s", w + "es"]
    if w.endswith("e"):
        forms += [w + "d", w[:-1] + "ing"]
    else:
        forms += [w + "ed", w + "ing"]
    if last in consonants and not w.endswith("e"):
        forms += [w + last + "ed", w + last + "ing"]
    if "-" in w:
        forms += [w.replace("-", " "), w.replace("-", "")]
    alts = [re.escape(x) for x in dict.fromkeys(forms)]
    pat = re.compile(rf"\b(?:{'|'.join(alts)})\b", flags=re.I)
    return bool(pat.search(s))


def looks_like_full_sentence(s: str) -> bool:
    s = s.strip()
    if len(s) < 12 or len(s.split()) < 4:
        return False
    if not s or s[-1] not in ".?!":
        return False
    if not s[0].isalpha() or not s[0].isupper():
        return False
    if "/" in s:
        return False
    lowered = re.sub(r"[^a-zA-Z'\- ]+", " ", s).lower()
    words = [w for w in lowered.split() if w]
    if len(words) < 4:
        return False
    if any(w in AUXILIARIES for w in words):
        return True
    for w in words:
        if w.endswith(("ed", "ing")) and len(w) > 4:
            return True
        if w.endswith("s") and len(w) > 3 and w not in {"this", "thus"}:
            return True
    return False


def corpus_entries(text: str) -> List[str]:
    m = re.search(r"(?m)^>[ \t]*\[!example\]-[ \t]*语料(?:[ \t].*)?\r?\n", text)
    if not m:
        return []
    pos = m.end()
    entries = []
    while pos < len(text):
        line_end = text.find("\n", pos)
        if line_end == -1:
            line_end = len(text)
        line = text[pos:line_end]
        if not line.startswith(">"):
            break
        mm = re.match(r"^>\s*-\s+(.*)$", line)
        if mm:
            entries.append(mm.group(1).rstrip())
        pos = line_end + 1
    return entries


def validate_file(relpath: str) -> Tuple[List[str], int]:
    path = REPO / relpath
    word = path.stem
    text = read_text(path)
    word_freq = extract_word_freq(text)
    entries = corpus_entries(text)
    errors: List[str] = []
    if not entries:
        return ["缺少语料条目"], 0

    for idx, raw in enumerate(entries, 1):
        if PLACEHOLDER_RE.search(raw):
            errors.append(f"语料{idx}: 含占位伪句或 NoSource")
        tag_m = TAG_RE.search(raw)
        if not tag_m:
            errors.append(f"语料{idx}: 非法或缺失 tag")
            sent = re.sub(r"`\[[^\]]+\]`\s*$", "", raw).rstrip()
        else:
            sent = TAG_RE.sub("", raw).rstrip()
        if re.search(r"[\u4e00-\u9fff]", sent):
            errors.append(f"语料{idx}: 含中文残留")
        if sent and sent[-1] not in ".?!":
            errors.append(f"语料{idx}: tag 前缺少句末标点")
        if not keep_if_contains_word(word, sent):
            errors.append(f"语料{idx}: 未包含目标词")
        if not looks_like_full_sentence(sent):
            errors.append(f"语料{idx}: 不是完整英文句")

    req = required_corpus_count(word_freq)
    if len(entries) < req:
        errors.append(f"语料数量不足: have={len(entries)} required={req}")
    return errors, len(entries)


def main() -> None:
    target_group = sys.argv[1] if len(sys.argv) > 1 else "executed"
    relpaths = []
    for scope in get_scopes(target_group if target_group in {"early", "executed"} else "all"):
        list_file = Path(scope["list_path"])
        relpaths.extend([ln.strip() for ln in read_text(list_file).splitlines() if ln.strip()])

    bad_files = []
    bad_txt = []
    for rel in relpaths:
        errors, count = validate_file(rel)
        if errors:
            bad_files.append({"relpath": rel, "corpus_count": count, "errors": errors})
            bad_txt.append(rel)
            for err in errors:
                bad_txt.append(f"  - {err}")

    REPORT.write_text(
        json.dumps(
            {
                "files_total": len(relpaths),
                "bad_count": len(bad_files),
                "bad_files": bad_files,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    BAD_TXT.write_text("\n".join(bad_txt) + "\n", encoding="utf-8")
    print(f"bad_count={len(bad_files)}")
    print(f"report={REPORT}")
    print(f"bad_txt={BAD_TXT}")


if __name__ == "__main__":
    main()
