#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 alignment scope 内的词条执行统一扫描，输出结构与语料问题清单。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_alignment_rules import (
    has_fake_exam_tag,
    is_function_word_invalid_usage,
    is_semantic_mismatch,
    is_template_corpus,
    parse_corpus_entries,
    scan_output_issues as common_scan_output_issues,
)


REPO = Path("/workspace/Obsidian-Eg")
SCOPE_JSON = Path("/data/user/work/alignment_scope.json")
OUT_JSON = Path("/data/user/work/alignment_manifest.json")
OUT_SUMMARY_JSON = Path("/data/user/work/alignment_manifest_summary.json")
VALID_TAG_RE = re.compile(r"`\[(?:例|真题|考研-[^\]]+|COCA(?:-[^\]]+)?|BNC(?:-[^\]]+)?)\]`\s*$")
ANY_TAG_RE = re.compile(r"`\[[^\]]+\]`\s*$")
OPTION_CHAIN_RE = re.compile(r"\bA\.\s+.+\bB\.\s+.+\bC\.\s+", flags=re.I)
BLANK_RE = re.compile(r"_{2,}|\b__\b")
MASTERY_TAG_RE = re.compile(r"(?m)^\s*-\s*掌握/L\d+\s*$")
CALL_OUT_LEVEL_RE = re.compile(r"(?m)^>\s*\[![^\]]+\]-\s*.+\s·\sL\d+\s*$")
AUXILIARIES = {
    "am", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did",
    "have", "has", "had",
    "can", "could", "may", "might", "must", "shall", "should", "will", "would",
}

COMMON_VERBS = {
    "need",
    "needs",
    "needed",
    "see",
    "sees",
    "saw",
    "give",
    "gives",
    "gave",
}


def detect_structure_issues(text: str) -> List[str]:
    issues: List[str] = []
    if re.search(r"(?m)^mastery:\s*", text):
        issues.append("old_mastery")
    if MASTERY_TAG_RE.search(text):
        issues.append("old_tag_mastery")
    if CALL_OUT_LEVEL_RE.search(text):
        issues.append("old_callout_level_suffix")
    if re.search(r"(?m)^##\s+复习记录\s*$", text):
        issues.append("old_review_section")
    return issues


def required_corpus_count(word_freq: str) -> int:
    return 2 if word_freq == "超纲词" else 3


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


def strip_tag(raw: str) -> Tuple[str, str]:
    m = VALID_TAG_RE.search(raw)
    if not m:
        return re.sub(r"`\[[^\]]+\]`\s*$", "", raw).strip(), ""
    tag = m.group(0).strip("`")
    sent = VALID_TAG_RE.sub("", raw).rstrip()
    return sent, tag


def normalize_sentence(s: str) -> str:
    s = re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()
    s = s.strip('"\'“”‘’')
    s = s.rstrip('"\'“”‘’').strip()
    return s


def keep_if_contains_word(word: str, s: str) -> bool:
    w = word.lower().strip()
    if not w:
        return False
    base_forms = {w}
    if "-" in w:
        base_forms.add(w.replace("-", " "))
        base_forms.add(w.replace("-", ""))
    if " " in w:
        base_forms.add(w.replace(" ", "-"))
        base_forms.add(w.replace(" ", ""))

    forms = set()
    consonants = "bcdfghjklmnpqrstvwxyz"
    for base in base_forms:
        if not base:
            continue
        last = base[-1]
        forms.update({base, base + "s", base + "es"})
        if base == "sow":
            forms.add("sown")
        if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
            forms.update({base[:-1] + "ied", base[:-1] + "ies", base[:-1] + "ying"})
        if base.endswith("e"):
            forms.update({base + "d", base[:-1] + "ing"})
        else:
            forms.update({base + "ed", base + "ing"})
        if last in consonants and not base.endswith("e"):
            forms.update({base + last + "ed", base + last + "ing"})
    pat = re.compile(rf"\b(?:{'|'.join(re.escape(x) for x in sorted(forms))})\b", flags=re.I)
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
    if any(w in COMMON_VERBS for w in words):
        return True
    for w in words:
        if w.endswith(("ed", "ing")) and len(w) > 4:
            return True
        if w.endswith("s") and len(w) > 3 and w not in {"this", "thus"}:
            return True
    return False


def has_explanation_or_mcq_residue(s: str) -> bool:
    return bool(OPTION_CHAIN_RE.search(s) or BLANK_RE.search(s) or re.search(r"[—-]{2,}", s))


def sentence_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_sentence(s).lower()).strip()


def scan_corpus_issues(
    text: str,
    word: str,
    word_freq: str,
    pos: str = "",
    semantic_field: str = "",
) -> List[str]:
    issues: List[str] = []
    block = corpus_block(text)
    if not block:
        return ["missing_corpus_block"]

    entries = parse_corpus_entries(block)
    if not entries:
        return ["missing_corpus_bullets"]

    seen = set()
    for idx, entry in enumerate(entries, 1):
        raw = entry["raw"]
        sent, tag = strip_tag(raw)
        norm = normalize_sentence(sent)
        if not tag:
            if ANY_TAG_RE.search(raw):
                issues.append(f"entry_{idx}_invalid_tag")
            else:
                issues.append(f"entry_{idx}_missing_tag")
        if tag and not VALID_TAG_RE.search(raw):
            issues.append(f"entry_{idx}_invalid_tag")
        if re.search(r"[\u4e00-\u9fff]", norm):
            issues.append(f"entry_{idx}_chinese_residue")
        if re.search(r"\s+[.?!]$", norm):
            issues.append(f"entry_{idx}_space_before_punctuation")
        if has_explanation_or_mcq_residue(norm):
            issues.append(f"entry_{idx}_explanation_or_mcq_residue")
        if is_template_corpus(norm, word):
            issues.append(f"entry_{idx}_template_corpus")
        if has_fake_exam_tag(norm, tag, word):
            issues.append(f"entry_{idx}_fake_exam_tag")
        if is_function_word_invalid_usage(word, norm, pos):
            issues.append(f"entry_{idx}_function_word_invalid_usage")
        if is_semantic_mismatch(word, norm, pos, semantic_field):
            issues.append(f"entry_{idx}_semantic_mismatch")
        if not looks_like_full_sentence(norm):
            issues.append(f"entry_{idx}_not_full_sentence")
        if norm and not keep_if_contains_word(word, norm):
            issues.append(f"entry_{idx}_missing_target_word")
        if not entry.get("translation", "").strip():
            issues.append(f"entry_{idx}_missing_translation")
        source_name = entry.get("source_name", "").strip()
        if not source_name:
            issues.append(f"entry_{idx}_missing_source")
        elif source_name == "Browser":
            issues.append(f"entry_{idx}_source_name_is_browser")
        if not entry.get("source_url", "").strip():
            issues.append(f"entry_{idx}_missing_source_url")
        key = sentence_key(norm)
        if key:
            if key in seen:
                issues.append("duplicate_sentence")
            seen.add(key)

    if len(entries) < required_corpus_count(word_freq):
        issues.append("insufficient_corpus_count")
    return issues


def scan_output_issues(text: str) -> List[str]:
    return common_scan_output_issues(text)


def scan_file(relpath: str) -> Dict[str, object]:
    path = REPO / relpath
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^word_freq:\s*(.+?)\s*$", text, flags=re.M)
    pos_m = re.search(r"^pos:\s*(.+?)\s*$", text, flags=re.M)
    field_m = re.search(r"^semantic_field:\s*(.+?)\s*$", text, flags=re.M)
    word_freq = (m.group(1).strip() if m else "").strip('"').strip("'")
    pos = (pos_m.group(1).strip() if pos_m else "").strip('"').strip("'")
    semantic_field = (field_m.group(1).strip() if field_m else "").strip('"').strip("'")
    word = path.stem
    structure_issues = detect_structure_issues(text)
    corpus_issues = scan_corpus_issues(text, word, word_freq, pos, semantic_field)
    output_issues = scan_output_issues(text)
    return {
        "relpath": relpath,
        "word": word,
        "word_freq": word_freq,
        "structure_issues": structure_issues,
        "corpus_issues": corpus_issues,
        "output_issues": output_issues,
        "problem_flags": structure_issues + corpus_issues + output_issues,
    }


def main() -> None:
    scope = json.loads(SCOPE_JSON.read_text(encoding="utf-8"))
    items = []
    counter = Counter()
    for item in scope["items"]:
        relpath = item["relpath"]
        if not (REPO / relpath).exists():
            continue
        scanned = scan_file(relpath)
        scanned["source_scope"] = item.get("source_scope", [])
        items.append(scanned)
        counter.update(scanned["problem_flags"])
    OUT_JSON.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_SUMMARY_JSON.write_text(
        json.dumps(
            {
                "files_scanned": len(items),
                "files_with_problems": sum(1 for x in items if x["problem_flags"]),
                "problem_counts": dict(sorted(counter.items())),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"files_scanned={len(items)}")
    print(f"files_with_problems={sum(1 for x in items if x['problem_flags'])}")
    print(f"out={OUT_JSON}")


if __name__ == "__main__":
    main()
