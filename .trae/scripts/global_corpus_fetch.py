#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_alignment_rules import normalize_sentence
from p2_template_fetch import (
    REPO,
    candidate_allowed,
    extract_existing_good_entries,
    load_browser_hits,
    make_browser_queue_item,
    merge_browser_hits_for_item,
    required_corpus_count,
    trusted_entry,
    unique_candidates,
    word_forms,
)
from manual_review_fetch_39_41 import build_exam_cache, fetch_cambridge, fetch_exam_candidates, fetch_mw, fetch_oxford
from global_corpus_workdir import work_path


SCOPE_JSON = work_path("global_corpus_scope.json")
INVENTORY_JSON = work_path("global_corpus_inventory.json")
OUT_JSON = work_path("global_corpus_candidates.json")
OUT_BROWSER_QUEUE = work_path("global_corpus_browser_queue.json")


def key_for_sentence(sentence: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_sentence(sentence).lower()).strip()


def find_exact_verified_candidate(original_sentence: str, static_candidates: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    target = normalize_sentence(original_sentence)
    for item in static_candidates:
        if normalize_sentence(item["sentence"]) == target:
            return item
    return None


def global_candidate_allowed(item: Dict[str, str], word: str, pos: str, semantic_field: str) -> bool:
    source = str(item.get("source", "")).strip()
    if source in {"", "Unknown", "NoSource", "Browser"}:
        return False
    if not str(item.get("translation", "")).strip():
        return False
    return candidate_allowed(item, word, pos, semantic_field)


def resolve_entry_from_static_candidates(
    existing_entry: Dict[str, object],
    static_candidates: List[Dict[str, str]],
    pos: str,
    semantic_field: str,
) -> Dict[str, str]:
    word = str(existing_entry["word"])
    original_sentence = str(existing_entry["original_sentence"])
    original_tag = str(existing_entry["original_tag"])

    exact = find_exact_verified_candidate(original_sentence, static_candidates)
    if exact and global_candidate_allowed(exact, word, pos, semantic_field):
        return {
            "sentence": normalize_sentence(original_sentence),
            "tag": original_tag,
            "translation": exact.get("translation", "").strip(),
            "source": exact.get("source", "").strip(),
            "url": exact.get("url", "").strip(),
        }

    for cand in static_candidates:
        if global_candidate_allowed(cand, word, pos, semantic_field):
            return {
                "sentence": normalize_sentence(cand["sentence"]),
                "tag": "[例]",
                "translation": cand.get("translation", "").strip(),
                "source": cand.get("source", "").strip(),
                "url": cand.get("url", "").strip(),
            }
    return {}


def build_inventory_index(items: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for item in items:
        grouped[str(item["relpath"])].append(item)
    return grouped


def build_final_entries_for_item(
    inventory_entries: List[Dict[str, object]],
    kept_entries: List[Dict[str, str]],
    static_candidates: List[Dict[str, str]],
    browser_candidates: List[Dict[str, str]],
    word: str,
    word_freq: str,
    pos: str,
    semantic_field: str,
) -> Dict[str, object]:
    req = required_corpus_count(word_freq)
    kept_by_key = {key_for_sentence(item["sentence"]): item for item in kept_entries}
    used_keys = set()
    final_entries: List[Dict[str, str]] = []
    entry_actions: Dict[str, str] = {}
    preserved_entry_ids: List[str] = []
    replaced_entry_ids: List[str] = []
    blocked_reasons: List[str] = []
    candidate_sources = Counter()
    pending_fill_targets: List[Dict[str, str]] = []

    def append_entry(entry: Dict[str, str], entry_id: str, action: str) -> bool:
        key = key_for_sentence(entry.get("sentence", ""))
        if not key or key in used_keys:
            return False
        if not global_candidate_allowed(entry, word, pos, semantic_field):
            return False
        used_keys.add(key)
        final_entries.append(entry)
        entry_actions[entry_id] = action
        candidate_sources[entry.get("source", "").strip() or "Unknown"] += 1
        return True

    actionable_entries: List[Dict[str, object]] = []
    for inv in inventory_entries:
        entry_id = str(inv.get("entry_id", ""))
        sentence_key = str(inv.get("sentence_key") or key_for_sentence(str(inv.get("original_sentence", ""))))
        action = str(inv.get("preferred_action", "external_refetch"))
        if action == "keep_verified":
            existing = kept_by_key.get(sentence_key)
            if existing and append_entry(existing, entry_id, "keep_verified"):
                preserved_entry_ids.append(entry_id)
            else:
                blocked_reasons.append(f"{entry_id}:verified_keep_missing")
                actionable_entries.append({**inv, "preferred_action": "external_refetch"})
            continue
        actionable_entries.append(inv)

    for inv in actionable_entries:
        entry_id = str(inv.get("entry_id", ""))
        action = str(inv.get("preferred_action", "external_refetch"))
        resolved = resolve_entry_from_static_candidates(inv, static_candidates, pos, semantic_field)
        if resolved and append_entry(resolved, entry_id, action):
            if action == "preserve_sentence_and_backfill":
                preserved_entry_ids.append(entry_id)
            else:
                replaced_entry_ids.append(entry_id)
        else:
            blocked_reasons.append(f"{entry_id}:{action}_unresolved")
            pending_fill_targets.append({"entry_id": entry_id, "action": action})

    for idx, item in enumerate(static_candidates):
        if len(final_entries) >= req:
            break
        target = pending_fill_targets[0] if pending_fill_targets else None
        target_id = target["entry_id"] if target else f"static-fill:{idx+1}"
        action = target["action"] if target else "static_fill"
        if append_entry(item, target_id, action):
            replaced_entry_ids.append(target_id)
            if target:
                pending_fill_targets.pop(0)

    for idx, item in enumerate(browser_candidates):
        if len(final_entries) >= req:
            break
        target = pending_fill_targets[0] if pending_fill_targets else None
        target_id = target["entry_id"] if target else f"browser-fill:{idx+1}"
        action = target["action"] if target else "browser_fill"
        if append_entry(item, target_id, action):
            replaced_entry_ids.append(target_id)
            if target:
                pending_fill_targets.pop(0)

    unresolved = len(final_entries) < req
    if unresolved:
        blocked_reasons.append("required_count_unmet")
    return {
        "final_entries": final_entries,
        "entry_actions": entry_actions,
        "preserved_entry_ids": preserved_entry_ids,
        "replaced_entry_ids": replaced_entry_ids,
        "newly_added_entries": max(0, len(final_entries) - len(preserved_entry_ids)),
        "candidate_source_breakdown": dict(candidate_sources),
        "blocked_reasons": blocked_reasons,
        "unresolved": unresolved,
    }


def main() -> None:
    scope = json.loads(SCOPE_JSON.read_text(encoding="utf-8"))["items"]
    inventory_payload = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    inventory_by_relpath = build_inventory_index(inventory_payload.get("items", []))
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
        inventory_entries = inventory_by_relpath.get(str(item["relpath"]), [])
        req = required_corpus_count(item["word_freq"])
        static_candidates: List[Dict[str, str]] = []

        def absorb(cands: List[Dict[str, str]]) -> None:
            for cand in cands:
                if trusted_entry(cand) and global_candidate_allowed(cand, item["word"], pos, semantic_field):
                    static_candidates.append(cand)

        inventory_actions_needed = any(
            str(inv.get("preferred_action", "")) != "keep_verified" for inv in inventory_entries
        )
        file_verified_count = sum(1 for inv in inventory_entries if inv.get("status") == "verified_keep")

        decision = build_final_entries_for_item(
            inventory_entries=inventory_entries,
            kept_entries=kept,
            static_candidates=static_candidates,
            browser_candidates=[],
            word=item["word"],
            word_freq=item["word_freq"],
            pos=pos,
            semantic_field=semantic_field,
        )
        if len(decision["final_entries"]) < req or inventory_actions_needed:
            for form in word_forms(item["word"]):
                absorb(fetch_exam_candidates(form, exam_map))
            static_candidates = unique_candidates(static_candidates)
            decision = build_final_entries_for_item(
                inventory_entries=inventory_entries,
                kept_entries=kept,
                static_candidates=static_candidates,
                browser_candidates=[],
                word=item["word"],
                word_freq=item["word_freq"],
                pos=pos,
                semantic_field=semantic_field,
            )
        if len(decision["final_entries"]) < req:
            for form in word_forms(item["word"]):
                absorb(fetch_cambridge(form))
            static_candidates = unique_candidates(static_candidates)
            decision = build_final_entries_for_item(
                inventory_entries=inventory_entries,
                kept_entries=kept,
                static_candidates=static_candidates,
                browser_candidates=[],
                word=item["word"],
                word_freq=item["word_freq"],
                pos=pos,
                semantic_field=semantic_field,
            )
        if len(decision["final_entries"]) < req:
            for form in word_forms(item["word"]):
                absorb(fetch_oxford(form))
            static_candidates = unique_candidates(static_candidates)
            decision = build_final_entries_for_item(
                inventory_entries=inventory_entries,
                kept_entries=kept,
                static_candidates=static_candidates,
                browser_candidates=[],
                word=item["word"],
                word_freq=item["word_freq"],
                pos=pos,
                semantic_field=semantic_field,
            )
        if len(decision["final_entries"]) < req:
            for form in word_forms(item["word"]):
                absorb(fetch_mw(form))
            static_candidates = unique_candidates(static_candidates)
            decision = build_final_entries_for_item(
                inventory_entries=inventory_entries,
                kept_entries=kept,
                static_candidates=static_candidates,
                browser_candidates=[],
                word=item["word"],
                word_freq=item["word_freq"],
                pos=pos,
                semantic_field=semantic_field,
            )

        browser_candidates: List[Dict[str, str]] = []
        if len(decision["final_entries"]) < req:
            browser_candidates = [
                cand
                for cand in merge_browser_hits_for_item(
                    browser_hits,
                    scope_id=str(item["scope_id"]),
                    relpath=str(item["relpath"]),
                    word=str(item["word"]),
                    pos=pos,
                    semantic_field=semantic_field,
                )
                if global_candidate_allowed(cand, item["word"], pos, semantic_field)
            ]
            decision = build_final_entries_for_item(
                inventory_entries=inventory_entries,
                kept_entries=kept,
                static_candidates=static_candidates,
                browser_candidates=browser_candidates,
                word=item["word"],
                word_freq=item["word_freq"],
                pos=pos,
                semantic_field=semantic_field,
            )

        results.append(
            {
                **item,
                "inventory_verified_count": file_verified_count,
                "inventory_actionable_count": sum(1 for inv in inventory_entries if inv.get("status") != "verified_keep"),
                "final_entries": decision["final_entries"],
                "entry_actions": decision["entry_actions"],
                "preserved_entry_ids": decision["preserved_entry_ids"],
                "replaced_entry_ids": decision["replaced_entry_ids"],
                "newly_added_entries": decision["newly_added_entries"],
                "candidate_count": len(static_candidates) + len(kept) + len(browser_candidates),
                "candidate_sources": {
                    "keep_existing": len(kept),
                    "static": len(static_candidates),
                    "browser": len(browser_candidates),
                },
                "candidate_source_breakdown": decision["candidate_source_breakdown"],
                "blocked_reasons": decision["blocked_reasons"],
                "unresolved": decision["unresolved"],
                "unresolved_reasons": ["strict_verified_candidates_insufficient"] if decision["unresolved"] else [],
            }
        )
        if decision["unresolved"]:
            queue_item = make_browser_queue_item(item["scope_id"], item["relpath"], item["word"], req)
            queue_item["missing_count"] = max(0, req - len(decision["final_entries"]))
            queue_item["existing_verified_count"] = file_verified_count
            queue_item["preferred_sources"] = ["Exam", "Cambridge", "Oxford", "Merriam-Webster"]
            queue_item["rejected_sentence_keys"] = [
                str(inv.get("sentence_key", "")) for inv in inventory_entries if inv.get("status") != "verified_keep"
            ]
            browser_queue.append(queue_item)
    OUT_JSON.write_text(json.dumps({"items": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_BROWSER_QUEUE.write_text(json.dumps({"items": browser_queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"problem_items={len(results)}")
    print(f"browser_queue={len(browser_queue)}")


if __name__ == "__main__":
    main()
