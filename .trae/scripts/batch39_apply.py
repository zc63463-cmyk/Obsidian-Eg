#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第39批（L0_超纲词 第9批：801–900）离线 apply：
- 仅修改：
  1) ## 核心释义（6.5：补反引号句型；每义项≤2）
  2) > [!example]- 语料（6.6：清洗为完整英文句；保留合法 tag，不足则记录待联网补齐）
- 已完成则跳过对应修正：
  - 6.5：按“缺啥补啥”补齐（不重复添加）
  - 6.6：语料若已符合“完整句 + 合法 tag + 无中文残留 + tag前有句末标点 + 包含目标词”，则跳过
输出：
- /data/user/work/batch39_needs_online.tsv
- /data/user/work/batch39_apply_stats.json
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from batch39_validate import (
    VALID_TAG_RE,
    keep_if_contains_word,
    looks_like_full_sentence,
    required_corpus_count,
    strip_tag,
)


REPO = Path("/workspace/Obsidian-Eg")
LIST_FILE = REPO / ".trae" / "batches" / "batch39_files.txt"
NEEDS_ONLINE = Path("/data/user/work/batch39_needs_online.tsv")
STATS_JSON = Path("/data/user/work/batch39_apply_stats.json")

DIGITS = "①②③④⑤⑥⑦⑧⑨⑩"
ANY_TAG_RE = re.compile(r"`\[[^\]]+\]`\s*$")


def read_text(p: Path) -> str:
    with p.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def write_text(p: Path, text: str) -> None:
    with p.open("w", encoding="utf-8", newline="") as f:
        f.write(text)


def extract_frontmatter_word_freq(text: str) -> str:
    m = re.search(r"^word_freq:\s*(.+?)\s*$", text, flags=re.M)
    return (m.group(1).strip() if m else "").strip('"').strip("'")


@dataclass
class Span:
    start: int
    end: int


def find_section_span(text: str, header: str) -> Optional[Span]:
    m = re.search(rf"(?m)^[ \t]*##[ \t]+{re.escape(header)}[ \t]*\r?\n", text)
    if not m:
        return None
    start = m.start()
    m2 = re.search(r"(?m)^[ \t]*##[ \t]+", text[m.end() :])
    end = (m.end() + m2.start()) if m2 else len(text)
    return Span(start=start, end=end)


def corpus_block_span(text: str) -> Optional[Span]:
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
    return Span(start=start, end=pos)


def normalize_core_meaning_markups(core_text: str) -> str:
    def repl(m: re.Match) -> str:
        digit = m.group(1)
        meaning = m.group(2).strip()
        return f"{digit}==**{meaning}**=="

    pattern = rf"([{DIGITS}])(?!=)([^；\r\n]+)"
    out = re.sub(pattern, repl, core_text)
    out = re.sub(r"==\*\*\s*(.+?)\s*\*\*：([^；\r\n]+)(?=[；\r\n])", r"==**\1：\2**==", out)
    return out


def pick_pattern(pos: str, meaning_zh: str) -> Optional[str]:
    pos = pos.strip().lower()
    pos = re.sub(r"\s+", "", pos)
    pos = re.sub(r"[^a-z.]+", "", pos)
    pos = re.sub(r"\.{2,}", ".", pos)
    meaning_zh = meaning_zh.strip()
    if "被动" in pos:
        return "be V-ed to N"
    if "vt" in pos:
        return "V N"
    if "vi" in pos:
        return "V"
    if pos in {"v.", "v"}:
        if meaning_zh.startswith(("使", "让", "令", "把")):
            return "V N"
        return "V"
    if pos.startswith("n"):
        return "N"
    if pos.startswith("adj") or pos in {"a.", "a"} or pos.startswith("a."):
        return "adj"
    if pos.startswith("adv"):
        return "adv"
    if pos.startswith("prep"):
        return "prep N"
    if pos.startswith("int"):
        return "int"
    if pos.startswith("conj"):
        return "that-clause"
    if pos.startswith("pron"):
        return "pron"
    return None


MEANING_NEED_RE = re.compile(rf"([{DIGITS}])==\*\*(.+?)\*\*==(?!\s*`)")
MEANING_ALL_RE = re.compile(rf"([{DIGITS}])==\*\*(.+?)\*\*==")


def apply_65(core_text: str) -> Tuple[str, bool]:
    core_text2 = normalize_core_meaning_markups(core_text)
    changed = False
    out_lines: List[str] = []
    current_pos: Optional[str] = None

    for line in core_text2.splitlines(keepends=True):
        mpos = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", line.strip("\r\n"))
        if mpos:
            current_pos = mpos.group(1)
            pos = current_pos
        else:
            pos = current_pos
            if not pos:
                out_lines.append(line)
                continue

        def add_pat(mm: re.Match) -> str:
            nonlocal changed
            digit = mm.group(1)
            meaning = mm.group(2)
            pat = pick_pattern(pos, meaning)
            if not pat:
                return mm.group(0)
            changed = True
            return f"{digit}==**{meaning}**== `{pat}`"

        newline = re.sub(r"==（[^）]*）\*\*(.+?)\*\*==", r"==**\1**==", line)
        newline = MEANING_NEED_RE.sub(add_pat, newline)

        def ensure_pat(mm: re.Match) -> str:
            nonlocal changed
            digit = mm.group(1)
            meaning = mm.group(2)
            tail = newline[mm.start() : mm.start() + 120]
            if re.search(rf"{re.escape(digit)}==\*\*.+?\*\*==\s*`", tail):
                return mm.group(0)
            pat = pick_pattern(pos, meaning)
            if not pat:
                return mm.group(0)
            changed = True
            return f"{digit}==**{meaning}**== `{pat}`"

        newline = MEANING_ALL_RE.sub(ensure_pat, newline)
        out_lines.append(newline)

    return "".join(out_lines), changed


def bullets_from_corpus_block(block: str) -> List[str]:
    bullets = []
    for ln in block.splitlines():
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if m:
            bullets.append(m.group(1).rstrip())
    return bullets


def is_66_done(corpus_block: str, word: str, word_freq: str) -> bool:
    bullets = bullets_from_corpus_block(corpus_block)
    if not bullets:
        return False

    for b in bullets:
        sent, tag = strip_tag(b)
        if not tag:
            return False
        if re.search(r"[\u4e00-\u9fff]", sent):
            return False
        if not keep_if_contains_word(word, sent):
            return False
        if not looks_like_full_sentence(sent):
            return False

    req = required_corpus_count(word_freq)
    return len(bullets) >= req


def clean_bullet_text(raw: str) -> str:
    s = raw.strip()
    s = ANY_TAG_RE.sub("", s).rstrip()
    s = re.sub(r"（.*?）", "", s).strip()
    s = re.sub(r"（.*$", "", s).strip()
    s = re.sub(r"\([^)]*[\u4e00-\u9fff][^)]*\)", "", s).strip()
    s = re.sub(r"\(.*$", "", s).strip()
    s = re.split(r"[—-]{2,}", s)[0].strip()
    s = s.strip('"\'“”‘’')
    s = s.lstrip('"\'“”‘’').rstrip('"\'“”‘’')
    s = re.sub(r"\s+", " ", s).strip()
    if re.search(r"[\u4e00-\u9fff]", s):
        s = re.sub(r"[\u4e00-\u9fff]+", "", s)
        s = s.replace("：", ":").replace("，", ",").replace("。", ".")
        s = re.sub(r"\s+", " ", s).strip()
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    if s and s[-1] not in ".?!":
        s += "."
    return s


def extract_or_default_tag(raw: str) -> str:
    _, tag = strip_tag(raw)
    return tag or "[例]"


def apply_66(full_text: str, word: str, word_freq: str) -> Tuple[str, bool, int, int]:
    sp = corpus_block_span(full_text)
    if not sp:
        return full_text, False, 0, required_corpus_count(word_freq)

    block = full_text[sp.start : sp.end]
    if is_66_done(block, word, word_freq):
        bullets = bullets_from_corpus_block(block)
        req = required_corpus_count(word_freq)
        return full_text, False, len(bullets), max(0, req - len(bullets))

    lines = block.splitlines()
    new_lines: List[str] = []
    corpus_count = 0
    seen = set()

    for ln in lines:
        m = re.match(r"^(>\s*-\s+)(.*)$", ln)
        if not m:
            new_lines.append(ln)
            continue
        prefix, raw = m.group(1), m.group(2)
        sent = clean_bullet_text(raw)
        if not sent:
            continue
        if not keep_if_contains_word(word, sent):
            continue
        if not looks_like_full_sentence(sent):
            continue
        key = re.sub(r"[^a-z0-9]+", " ", sent.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        tag = extract_or_default_tag(raw)
        if not VALID_TAG_RE.search(f"x `{tag}`"):
            tag = "[例]"
        new_lines.append(f"{prefix}{sent} `{tag}`")
        corpus_count += 1

    new_block = "\n".join(new_lines) + ("\n" if block.endswith("\n") else "")
    new_text = full_text[: sp.start] + new_block + full_text[sp.end :]
    req = required_corpus_count(word_freq)
    return new_text, True, corpus_count, max(0, req - corpus_count)


def main() -> None:
    rels = [ln.strip() for ln in LIST_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    stats = {
        "files_total": len(rels),
        "6.5_changed": 0,
        "6.5_skipped": 0,
        "6.6_changed": 0,
        "6.6_skipped": 0,
        "needs_online_files": 0,
        "needs_online_sentences": 0,
    }
    needs_rows: List[str] = ["relpath\tword\tword_freq\trequired\thave\tmissing"]

    for rel in rels:
        p = REPO / rel
        word = Path(rel).stem
        text0 = read_text(p)
        text = text0
        word_freq = extract_frontmatter_word_freq(text)
        req = required_corpus_count(word_freq)

        core_span = find_section_span(text, "核心释义")
        if core_span:
            core = text[core_span.start : core_span.end]
            new_core, changed65 = apply_65(core)
            if changed65:
                text = text[: core_span.start] + new_core + text[core_span.end :]
                stats["6.5_changed"] += 1
            else:
                stats["6.5_skipped"] += 1
        else:
            stats["6.5_skipped"] += 1

        text2, changed66, have, missing = apply_66(text, word, word_freq)
        if changed66:
            text = text2
            stats["6.6_changed"] += 1
        else:
            stats["6.6_skipped"] += 1

        if missing > 0:
            stats["needs_online_files"] += 1
            stats["needs_online_sentences"] += missing
            needs_rows.append(f"{rel}\t{word}\t{word_freq}\t{req}\t{have}\t{missing}")

        if text != text0:
            write_text(p, text)

    NEEDS_ONLINE.write_text("\n".join(needs_rows) + "\n", encoding="utf-8")
    STATS_JSON.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"Wrote needs_online -> {NEEDS_ONLINE}")


if __name__ == "__main__":
    main()
