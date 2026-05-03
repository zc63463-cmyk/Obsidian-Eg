#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第39批（L0_超纲词 第9批：801–900）校验：
- 仅检查规则，不改文件
- 接受 `[例]` / `[真题]` / `[考研-...]`，并兼容已存在的 COCA/BNC 标签
- 拒绝选择题题干、填空残片、列表式伪完整句
输出：
- /data/user/work/batch39_validate_report.json
- /data/user/work/batch39_validate_bad.txt
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


REPO = Path("/workspace/Obsidian-Eg")
LIST_FILE = REPO / ".trae" / "batches" / "batch39_files.txt"
REPORT = Path("/data/user/work/batch39_validate_report.json")
BAD_TXT = Path("/data/user/work/batch39_validate_bad.txt")

DIGITS = "①②③④⑤⑥⑦⑧⑨⑩"
VALID_TAG_RE = re.compile(
    r"`\[(?:例|真题|考研-[^\]]+|COCA(?:-[^\]]+)?|BNC(?:-[^\]]+)?)\]`\s*$"
)
OPTION_CHAIN_RE = re.compile(r"\bA\.\s+.+\bB\.\s+.+\bC\.\s+", flags=re.I)
BLANK_RE = re.compile(r"_{2,}|\b__\b")
AUXILIARIES = {
    "am","is","are","was","were","be","been","being","do","does","did",
    "have","has","had","can","could","may","might","must","shall","should","will","would",
}


def read_text(p: Path) -> str:
    with p.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def extract_frontmatter_word_freq(text: str) -> str:
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
    alts = [re.escape(x) for x in forms]
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
    if BLANK_RE.search(s):
        return False
    if OPTION_CHAIN_RE.search(s):
        return False
    if re.search(r"\b[0-9]{1,3}\.$", s):
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


def strip_tag(raw: str) -> Tuple[str, str]:
    m = VALID_TAG_RE.search(raw)
    if not m:
        return re.sub(r"`\[[^\]]+\]`\s*$", "", raw).strip(), ""
    tag = m.group(0).strip("`")
    sent = VALID_TAG_RE.sub("", raw).rstrip()
    return sent, tag


def find_section(text: str, header: str) -> str:
    m = re.search(rf"(?m)^[ \t]*##[ \t]+{re.escape(header)}[ \t]*\r?\n", text)
    if not m:
        return ""
    start = m.end()
    m2 = re.search(r"(?m)^[ \t]*##[ \t]+", text[start:])
    end = start + m2.start() if m2 else len(text)
    return text[m.start() : end]


def corpus_block(text: str) -> str:
    m = re.search(r"(?m)^>[ \t]*\[!example\]-[ \t]*语料(?:[ \t].*)?\r?\n", text)
    if not m:
        return ""
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
    return text[start:pos]


def validate_65(core: str) -> List[str]:
    errs: List[str] = []
    if not core:
        return ["缺少 ## 核心释义 区块"]
    parts = re.split(rf"([{DIGITS}])", core)
    if len(parts) < 3:
        return ["核心释义未发现义项编号(①②…)"]
    for i in range(1, len(parts), 2):
        digit = parts[i]
        seg = parts[i + 1]
        if "==**" in seg and not re.search(r"==\*\*.+?\*\*==\s*`[^`]+`", digit + seg):
            errs.append(f"{digit}: 释义后未紧跟句型反引号")
        n = len(re.findall(r"`[^`]+`", seg))
        if n == 0:
            errs.append(f"{digit}: 缺少句型反引号")
        if n > 2:
            errs.append(f"{digit}: 句型反引号超过2个({n})")
    return errs


def validate_66(text: str, word: str, word_freq: str) -> Tuple[List[str], int]:
    errs: List[str] = []
    block = corpus_block(text)
    if not block:
        return ["缺少 > [!example]- 语料 callout"], 0

    bullets = []
    for ln in block.splitlines():
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if not m:
            continue
        bullets.append(m.group(1).rstrip())

    if not bullets:
        errs.append("语料callout内缺少 > - 条目")
        return errs, 0

    for idx, b in enumerate(bullets, 1):
        sent, tag = strip_tag(b)
        if not tag:
            errs.append(f"语料{idx}: 行尾tag非法")
        if re.search(r"[\u4e00-\u9fff]", sent):
            errs.append(f"语料{idx}: 含中文残留")
        if sent and sent[-1] not in ".?!":
            errs.append(f"语料{idx}: tag前缺少句末标点(.?!)")
        if not looks_like_full_sentence(sent):
            errs.append(f"语料{idx}: 不是完整英文句")
        if sent and not keep_if_contains_word(word, sent):
            errs.append(f"语料{idx}: 未包含目标词")

    req = required_corpus_count(word_freq)
    if len(bullets) < req:
        errs.append(f"语料数量不足: have={len(bullets)} required={req}")

    return errs, len(bullets)


def main() -> None:
    rels = [ln.strip() for ln in LIST_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    report: Dict[str, object] = {"files_total": len(rels), "bad_files": [], "bad_count": 0}
    bad_lines: List[str] = []

    for rel in rels:
        p = REPO / rel
        word = Path(rel).stem
        text = read_text(p)
        word_freq = extract_frontmatter_word_freq(text)
        core = find_section(text, "核心释义")
        e65 = validate_65(core)
        e66, corpus_n = validate_66(text, word, word_freq)
        errs = e65 + e66
        if errs:
            report["bad_count"] = int(report["bad_count"]) + 1  # type: ignore[arg-type]
            report["bad_files"].append({"relpath": rel, "word": word, "word_freq": word_freq, "corpus_n": corpus_n, "errors": errs})  # type: ignore[index]
            bad_lines.append(rel)
            for e in errs:
                bad_lines.append(f"  - {e}")

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    BAD_TXT.write_text("\n".join(bad_lines) + "\n", encoding="utf-8")
    print(f"bad_files={report['bad_count']} / {report['files_total']}")
    print(f"report -> {REPORT}")


if __name__ == "__main__":
    main()
