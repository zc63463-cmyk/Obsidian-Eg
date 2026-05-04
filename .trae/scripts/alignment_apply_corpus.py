#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一修复语料区：
- 清理句末标点前空格
- 重写题干/片段型伪语料
- 去重
- 自动补足最低语料数量
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_alignment_rules import (
    has_fake_exam_tag,
    has_space_before_punctuation,
    is_function_word_invalid_usage,
    is_semantic_mismatch,
    is_template_corpus,
    keep_if_contains_word,
    looks_like_full_sentence,
    normalize_sentence,
    required_corpus_count,
    requires_rewrite,
    strip_tag,
)


REPO = Path("/workspace/Obsidian-Eg")
SCOPE_JSON = Path("/data/user/work/alignment_scope.json")
OUT_JSON = Path("/data/user/work/alignment_apply_corpus_stats.json")


def corpus_block_span(text: str) -> Tuple[int, int]:
    m = re.search(r"(?m)^>[ \t]*\[!example\]-[ \t]*语料(?:[ \t].*)?\r?\n", text)
    if not m:
        return -1, -1
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


def bullet_entries(block: str) -> List[str]:
    out: List[str] = []
    for ln in block.splitlines():
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if m:
            out.append(m.group(1).rstrip())
    return out


def sentence_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def clean_sentence(sent: str) -> str:
    sent = normalize_sentence(sent)
    sent = re.sub(r"\s+([.?!])$", r"\1", sent)
    if sent and sent[-1] not in ".?!":
        sent += "."
    return sent


def synthesize_example(word: str, pos: str, index: int) -> str:
    w = word.replace("-", " ")
    pos_l = (pos or "").lower()
    if "adj" in pos_l:
        templates = [
            f"The researchers proposed a {w} solution to the problem.",
            f"The company adopted a {w} approach to improve efficiency.",
            f"The plan offers a {w} option for small organizations.",
        ]
    elif "n" in pos_l:
        templates = [
            f"The report highlights the importance of {w} in the final decision.",
            f"The committee discussed the latest {w} during the meeting.",
            f"The article examines how {w} can shape public policy.",
        ]
    else:
        templates = [
            f"They decided to {w} the plan after further discussion.",
            f"The team continued to {w} the policy in response to new evidence.",
            f"Leaders must {w} the strategy when conditions change.",
        ]
    return templates[index % len(templates)]


def synthesize_p1_example(word: str, pos: str, semantic_field: str, index: int) -> str:
    w = word.replace("-", " ")
    wl = word.lower()
    if wl == "if":
        templates = [
            "If the evidence is weak, the committee will postpone the decision.",
            "Even if the plan is costly, some voters still support it.",
            "The manager asked if the report was ready for publication.",
        ]
        return templates[index % len(templates)]
    if wl == "and":
        templates = [
            "The course covers grammar and vocabulary at the same time.",
            "She opened the window and turned on the fan.",
            "Work hard, and you will see steady progress.",
        ]
        return templates[index % len(templates)]
    if wl == "for":
        templates = [
            "She saved money for graduate study abroad.",
            "The team searched for a more efficient solution.",
            "He stayed in Beijing for three years after graduation.",
        ]
        return templates[index % len(templates)]
    if wl == "while":
        templates = [
            "While the data are limited, the conclusion remains persuasive.",
            "She listened to music while she prepared the report.",
            "Some students prefer discussion, while others learn better alone.",
        ]
        return templates[index % len(templates)]
    if wl == "author":
        templates = [
            "The author revised the final chapter before the book was published.",
            "She became a respected author of modern historical fiction.",
            "The author explains the policy debate in clear and precise language.",
        ]
        return templates[index % len(templates)]
    if semantic_field == "自然物理":
        templates = [
            f"The hikers rested under a towering {w} near the coastal trail.",
            f"The cabin was built from durable {w} gathered in the region.",
            f"A line of {w} trees rose above the morning fog.",
        ]
        return templates[index % len(templates)]
    return synthesize_example(word, pos, index)


def rewrite_entry(word: str, pos: str, raw: str, index: int, semantic_field: str = "") -> str:
    sent, _ = strip_tag(raw)
    cleaned = clean_sentence(sent)
    if (
        not requires_rewrite(raw)
        and not is_template_corpus(cleaned, word)
        and not is_function_word_invalid_usage(word, cleaned, pos)
        and not is_semantic_mismatch(word, cleaned, pos, semantic_field)
        and keep_if_contains_word(word, cleaned)
        and looks_like_full_sentence(cleaned)
    ):
        return cleaned
    return synthesize_p1_example(word, pos, semantic_field, index)


def repair_corpus_text(
    text: str,
    word: str,
    word_freq: str,
    pos: str,
    semantic_field: str = "",
) -> Tuple[str, Dict[str, int]]:
    start, end = corpus_block_span(text)
    if start < 0:
        return text, {"rewritten": 0, "top_up_added": 0, "deduped": 0, "final_count": 0}

    block = text[start:end]
    entries = bullet_entries(block)
    stats = {"rewritten": 0, "top_up_added": 0, "deduped": 0, "final_count": 0}
    final_entries: List[str] = []
    seen = set()

    for idx, raw in enumerate(entries):
        sent, tag = strip_tag(raw)
        repaired = clean_sentence(sent)
        rewrite_needed = (
            requires_rewrite(raw)
            or is_template_corpus(repaired, word)
            or has_fake_exam_tag(repaired, tag, word)
            or is_function_word_invalid_usage(word, repaired, pos)
            or is_semantic_mismatch(word, repaired, pos, semantic_field)
        )
        if rewrite_needed:
            repaired = rewrite_entry(word, pos, raw, idx, semantic_field)
            stats["rewritten"] += 1
        if not keep_if_contains_word(word, repaired):
            repaired = rewrite_entry(word, pos, raw, idx, semantic_field)
            stats["rewritten"] += 1
        key = sentence_key(repaired)
        if key in seen:
            stats["deduped"] += 1
            continue
        seen.add(key)
        out_tag = "[例]" if has_fake_exam_tag(sent, tag, word) or rewrite_needed else (tag or "[例]")
        final_entries.append(f"> - {repaired} `{out_tag}`")

    req = required_corpus_count(word_freq)
    fill_index = 0
    while len(final_entries) < req:
        filler = synthesize_example(word, pos, fill_index)
        fill_index += 1
        key = sentence_key(filler)
        if key in seen:
            continue
        seen.add(key)
        final_entries.append(f"> - {filler} `[例]`")
        stats["top_up_added"] += 1

    stats["final_count"] = len(final_entries)
    new_block = "> [!example]- 语料\n" + "\n".join(final_entries) + "\n"
    new_text = text[:start] + new_block + text[end:]
    return new_text, stats


def main() -> None:
    scope = json.loads(SCOPE_JSON.read_text(encoding="utf-8"))
    summary = {"files_changed": 0, "rewritten": 0, "top_up_added": 0, "deduped": 0}
    for item in scope["items"]:
        relpath = item["relpath"]
        p = REPO / relpath
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        word_freq_m = re.search(r"^word_freq:\s*(.+?)\s*$", text, flags=re.M)
        pos_m = re.search(r"^pos:\s*(.+?)\s*$", text, flags=re.M)
        field_m = re.search(r"^semantic_field:\s*(.+?)\s*$", text, flags=re.M)
        word_freq = (word_freq_m.group(1).strip() if word_freq_m else "").strip('"').strip("'")
        pos = (pos_m.group(1).strip() if pos_m else "").strip('"').strip("'")
        semantic_field = (field_m.group(1).strip() if field_m else "").strip('"').strip("'")
        new_text, stats = repair_corpus_text(text, p.stem, word_freq, pos, semantic_field)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            summary["files_changed"] += 1
        for key in ("rewritten", "top_up_added", "deduped"):
            summary[key] += stats[key]
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
