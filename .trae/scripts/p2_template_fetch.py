#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_alignment_rules import (
    is_function_word_invalid_usage,
    is_semantic_mismatch,
    is_template_corpus,
    keep_if_contains_word,
    looks_like_full_sentence,
    normalize_sentence,
    parse_corpus_entries,
    required_corpus_count,
    requires_rewrite,
)
import manual_review_fetch_39_41 as mr
from manual_review_fetch_39_41 import (
    build_exam_cache,
    fetch_cambridge,
    fetch_exam_candidates,
    fetch_mw,
    fetch_oxford,
    trusted_entry,
)


REPO = Path("/workspace/Obsidian-Eg")
SCOPE_JSON = Path("/data/user/work/p2_template_corpus_scope.json")
OUT_JSON = Path("/data/user/work/p2_template_candidates.json")
OUT_BROWSER_QUEUE = Path("/data/user/work/p2_template_browser_queue.json")
BROWSER_HITS_JSON = Path(os.environ.get("P2_BROWSER_HITS_JSON", "/data/user/work/p2_template_browser_hits.json"))
mr.TIMEOUT = 8
WORD_ALIASES = {
    "characterise": ["characterize"],
    "paediatrics": ["pediatrics"],
}


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


def corpus_entries(text: str) -> List[str]:
    block = corpus_block(text)
    out: List[str] = []
    for ln in block.splitlines():
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if m:
            out.append(m.group(1).rstrip())
    return out


def unique_candidates(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out = []
    for item in items:
        key = re.sub(r"[^a-z0-9]+", " ", item["sentence"].lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def word_forms(word: str) -> List[str]:
    forms = [word]
    forms.extend(WORD_ALIASES.get(word.lower(), []))
    out: List[str] = []
    seen = set()
    for form in forms:
        key = form.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(form)
    return out


def sentence_matches_word(word: str, sentence: str) -> bool:
    return any(keep_if_contains_word(form, sentence) for form in word_forms(word))


def extract_existing_good_entries(text: str, word: str, pos: str, semantic_field: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for entry in parse_corpus_entries(corpus_block(text)):
        sent = entry["sentence"]
        tag = entry["tag"]
        norm = normalize_sentence(sent)
        if not tag:
            continue
        if requires_rewrite(entry["raw"]):
            continue
        if not looks_like_full_sentence(norm):
            continue
        if not sentence_matches_word(word, norm):
            continue
        if is_template_corpus(norm, word):
            continue
        if is_function_word_invalid_usage(word, norm, pos):
            continue
        if is_semantic_mismatch(word, norm, pos, semantic_field):
            continue
        source_name = entry.get("source_name", "").strip()
        source_url = entry.get("source_url", "").strip()
        translation = entry.get("translation", "").strip()
        if not source_name or not source_url or not translation:
            continue
        out.append(
            {
                "sentence": norm,
                "tag": tag,
                "translation": translation,
                "source": source_name,
                "url": source_url,
                "acquisition_mode": "existing",
            }
        )
    return unique_candidates(out)


def candidate_allowed(item: Dict[str, str], word: str, pos: str, semantic_field: str) -> bool:
    sent = normalize_sentence(item["sentence"])
    if not item.get("url"):
        return False
    if item.get("source") in {"Unknown", "NoSource", ""}:
        return False
    if requires_rewrite(item["sentence"]):
        return False
    if not looks_like_full_sentence(sent):
        return False
    if not sentence_matches_word(word, sent):
        return False
    if is_template_corpus(sent, word):
        return False
    if is_function_word_invalid_usage(word, sent, pos):
        return False
    if is_semantic_mismatch(word, sent, pos, semantic_field):
        return False
    return True


def choose_final_entries(
    kept: List[Dict[str, str]],
    static_candidates: List[Dict[str, str]],
    word: str,
    word_freq: str,
    pos: str,
    semantic_field: str,
) -> Tuple[List[Dict[str, str]], bool]:
    req = required_corpus_count(word_freq)
    final_entries: List[Dict[str, str]] = []
    for item in unique_candidates(kept + static_candidates):
        if candidate_allowed(item, word, pos, semantic_field):
            final_entries.append(item)
        if len(final_entries) >= req:
            break
    return final_entries, len(final_entries) < req


def make_browser_queue_item(scope_id: str, relpath: str, word: str, required_count: int) -> Dict[str, object]:
    urls: List[str] = []
    for form in word_forms(word):
        urls.extend(
            [
                f"https://dictionary.cambridge.org/dictionary/english/{quote(form)}",
                f"https://dictionary.cambridge.org/example/english/{quote(form)}",
                f"https://www.oxfordlearnersdictionaries.com/definition/english/{quote(form)}",
                f"https://www.merriam-webster.com/dictionary/{quote(form)}",
            ]
        )
    return {
        "scope_id": scope_id,
        "relpath": relpath,
        "word": word,
        "required_count": required_count,
        "reasons": ["strict_verified_candidates_insufficient"],
        "urls": list(dict.fromkeys(urls)),
    }


def load_browser_hits() -> List[Dict[str, str]]:
    if not BROWSER_HITS_JSON.exists():
        return []
    obj = json.loads(BROWSER_HITS_JSON.read_text(encoding="utf-8"))
    return [item for item in obj.get("items", []) if isinstance(item, dict)]


def merge_browser_hits_for_item(
    browser_hits: List[Dict[str, str]],
    scope_id: str,
    relpath: str,
    word: str,
    pos: str,
    semantic_field: str,
) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    for hit in browser_hits:
        if str(hit.get("relpath", "")) != relpath:
            continue
        hit_word = str(hit.get("word", "")).strip().lower()
        if hit_word not in {form.lower() for form in word_forms(word)}:
            continue
        if candidate_allowed(hit, word, pos, semantic_field):
            merged.append(hit)
    return unique_candidates(merged)


def main() -> None:
    scope = json.loads(SCOPE_JSON.read_text(encoding="utf-8"))["items"]
    exam_map = build_exam_cache()
    browser_hits = load_browser_hits()
    results = []
    browser_queue = []
    for item in scope:
        path = REPO / item["relpath"]
        text = path.read_text(encoding="utf-8")
        pos_m = re.search(r"^pos:\s*(.+?)\s*$", text, flags=re.M)
        field_m = re.search(r"^semantic_field:\s*(.+?)\s*$", text, flags=re.M)
        pos = (pos_m.group(1).strip() if pos_m else "").strip('"').strip("'")
        semantic_field = (field_m.group(1).strip() if field_m else "").strip('"').strip("'")
        kept = extract_existing_good_entries(text, item["word"], pos, semantic_field)
        req = required_corpus_count(item["word_freq"])
        static_candidates: List[Dict[str, str]] = []

        def absorb(cands: List[Dict[str, str]]) -> None:
            for cand in cands:
                if trusted_entry(cand):
                    static_candidates.append(cand)

        final_entries, unresolved = choose_final_entries(kept, static_candidates, item["word"], item["word_freq"], pos, semantic_field)
        if len(final_entries) < req:
            for form in word_forms(item["word"]):
                absorb(fetch_exam_candidates(form, exam_map))
            static_candidates = unique_candidates(static_candidates)
            final_entries, unresolved = choose_final_entries(kept, static_candidates, item["word"], item["word_freq"], pos, semantic_field)
        if len(final_entries) < req:
            for form in word_forms(item["word"]):
                absorb(fetch_cambridge(form))
            static_candidates = unique_candidates(static_candidates)
            final_entries, unresolved = choose_final_entries(kept, static_candidates, item["word"], item["word_freq"], pos, semantic_field)
        if len(final_entries) < req:
            for form in word_forms(item["word"]):
                absorb(fetch_oxford(form))
            static_candidates = unique_candidates(static_candidates)
            final_entries, unresolved = choose_final_entries(kept, static_candidates, item["word"], item["word_freq"], pos, semantic_field)
        if len(final_entries) < req:
            for form in word_forms(item["word"]):
                absorb(fetch_mw(form))
            static_candidates = unique_candidates(static_candidates)
            final_entries, unresolved = choose_final_entries(kept, static_candidates, item["word"], item["word_freq"], pos, semantic_field)
        if len(final_entries) < req:
            static_candidates.extend(
                merge_browser_hits_for_item(
                    browser_hits,
                    scope_id=str(item["scope_id"]),
                    relpath=str(item["relpath"]),
                    word=str(item["word"]),
                    pos=pos,
                    semantic_field=semantic_field,
                )
            )
            static_candidates = unique_candidates(static_candidates)
            final_entries, unresolved = choose_final_entries(kept, static_candidates, item["word"], item["word_freq"], pos, semantic_field)
        results.append(
            {
                **item,
                "final_entries": final_entries,
                "candidate_count": len(static_candidates) + len(kept),
                "candidate_sources": {
                    "keep_existing": len(kept),
                    "static": len(static_candidates),
                },
                "unresolved": unresolved,
                "unresolved_reasons": ["strict_verified_candidates_insufficient"] if unresolved else [],
            }
        )
        if unresolved:
            browser_queue.append(
                make_browser_queue_item(item["scope_id"], item["relpath"], item["word"], int(item["required_count"]))
            )
    OUT_JSON.write_text(json.dumps({"items": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_BROWSER_QUEUE.write_text(json.dumps({"items": browser_queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"problem_items={len(results)}")
    print(f"browser_queue={len(browser_queue)}")


if __name__ == "__main__":
    main()
