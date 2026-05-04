#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from typing import Dict, List, Tuple


VALID_TAG_RE = re.compile(
    r"`\[(?:例|真题|考研-[^\]]+|COCA(?:-[^\]]+)?|BNC(?:-[^\]]+)?)\]`\s*$"
)
OPTION_CHAIN_RE = re.compile(r"\bA\.\s+.+\bB\.\s+.+\bC\.\s+", flags=re.I)
BLANK_RE = re.compile(r"_{2,}|\b__\b")
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
TEMPLATE_PATTERNS = [
    re.compile(r"^The report highlights the importance of (?P<word>.+) in the final decision\.$", flags=re.I),
    re.compile(r"^The committee discussed the latest (?P<word>.+) during the meeting\.$", flags=re.I),
    re.compile(r"^The article examines how (?P<word>.+) can shape public policy\.$", flags=re.I),
    re.compile(r"^They decided to (?P<word>.+) the plan after further discussion\.$", flags=re.I),
    re.compile(r"^The team continued to (?P<word>.+) the policy in response to new evidence\.$", flags=re.I),
    re.compile(r"^Leaders must (?P<word>.+) the strategy when conditions change\.$", flags=re.I),
]
FUNCTION_WORDS = {
    "if", "while", "for", "and", "or", "but", "as", "than", "that",
    "when", "because", "since", "unless", "though", "although", "whether",
}
CONCRETE_FIELDS = {"自然物理"}
OUTPUT_PLACEHOLDER_RE = re.compile(r"<[^>]+>")
TRANSLATION_LINE_RE = re.compile(r"^>\s{2,}-\s*中译：\s*(.+?)\s*$")
SOURCE_LINE_RE = re.compile(r"^>\s{2,}-\s*来源：\s*(.+?)\s*\|\s*(https?://\S+)\s*$")


def required_corpus_count(word_freq: str) -> int:
    return 2 if word_freq == "超纲词" else 3


def normalize_sentence(s: str) -> str:
    s = re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()
    s = s.strip('"\'“”‘’')
    s = s.rstrip('"\'“”‘’').strip()
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def strip_tag(raw: str) -> Tuple[str, str]:
    m = VALID_TAG_RE.search(raw)
    if not m:
        return re.sub(r"`\[[^\]]+\]`\s*$", "", raw).strip(), ""
    tag = m.group(0).strip("`")
    sent = VALID_TAG_RE.sub("", raw).rstrip()
    return sent, tag


def parse_corpus_entries(block: str) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    current: Dict[str, str] | None = None
    for ln in block.splitlines():
        m_translation = TRANSLATION_LINE_RE.match(ln)
        if m_translation:
            if current is not None:
                current["translation"] = m_translation.group(1).strip()
            continue
        m_source = SOURCE_LINE_RE.match(ln)
        if m_source:
            if current is not None:
                current["source_name"] = m_source.group(1).strip()
                current["source_url"] = m_source.group(2).strip()
            continue
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if not m:
            continue
        raw = m.group(1).rstrip()
        sent, tag = strip_tag(raw)
        current = {
            "raw": raw,
            "sentence": sent,
            "tag": tag,
            "translation": "",
            "source_name": "",
            "source_url": "",
        }
        entries.append(current)
    return entries


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


def has_explanation_residue(s: str) -> bool:
    return bool(OPTION_CHAIN_RE.search(s) or BLANK_RE.search(s) or re.search(r"[—-]{2,}", s))


def has_space_before_punctuation(s: str) -> bool:
    return bool(re.search(r"\s+[.?!]$", s))


def is_template_corpus(sentence: str, word: str) -> bool:
    s = normalize_sentence(sentence)
    w = word.lower().replace("-", " ").strip()
    for pat in TEMPLATE_PATTERNS:
        m = pat.match(s)
        if not m:
            continue
        captured = m.group("word").lower().replace("-", " ").strip()
        if captured == w:
            return True
    return False


def has_fake_exam_tag(sentence: str, tag: str, word: str) -> bool:
    return tag == "[真题]" and is_template_corpus(sentence, word)


def is_function_word_invalid_usage(word: str, sentence: str, pos: str = "") -> bool:
    w = word.lower().strip()
    if w not in FUNCTION_WORDS:
        return False
    s = normalize_sentence(sentence)
    if is_template_corpus(s, w):
        return True
    low = s.lower()
    valid_if_patterns = ["if ", "even if ", "as if ", "only if ", "if only "]
    if w == "if":
        return not any(p in low for p in valid_if_patterns)
    return False


def is_semantic_mismatch(word: str, sentence: str, pos: str = "", semantic_field: str = "") -> bool:
    s = normalize_sentence(sentence)
    pos_l = (pos or "").lower()
    field = (semantic_field or "").strip()
    if not pos_l.startswith("n"):
        return False
    if field not in CONCRETE_FIELDS:
        return False
    return is_template_corpus(s, word)


def scan_output_issues(text: str) -> list[str]:
    issues: list[str] = []
    if "> [!success]- 内化标记" in text:
        issues.append("noncanonical_output_section_title")
    if OUTPUT_PLACEHOLDER_RE.search(text):
        issues.append("output_placeholder_residue")
    return issues


def requires_rewrite(raw: str) -> bool:
    s = normalize_sentence(strip_tag(raw)[0])
    if not s:
        return True
    if re.search(r"(?:\b[A-Za-z]\b\s+){6,}", s):
        return True
    if has_explanation_residue(s):
        return True
    if len(s.split()) < 4:
        return True
    if "/" in s:
        return True
    if not looks_like_full_sentence(s):
        return True
    return False
