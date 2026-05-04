#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from manual_review_fetch_39_41 import fetch_cambridge, fetch_mw, fetch_oxford, trusted_entry
from global_corpus_workdir import work_path


REPO = Path("/workspace/Obsidian-Eg")
FULL_SCOPE_JSON = work_path("global_corpus_scope.full.json")
SCOPE_JSON = work_path("global_corpus_scope.json")
VALIDATE_JSON = work_path("global_corpus_validate_report.json")
RAW_HITS_JSON = work_path("global_corpus_browser_hits_raw.json")
NORMALIZED_HITS_JSON = work_path("global_corpus_browser_hits.json")
TRANSLATION_CACHE_JSON = work_path("global_translation_cache.json")

ONLY_METADATA_ERRORS = {
    *(f"entry_{idx}_missing_translation" for idx in range(1, 7)),
    *(f"entry_{idx}_missing_source" for idx in range(1, 7)),
    *(f"entry_{idx}_missing_source_url" for idx in range(1, 7)),
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_repo_command(command: List[str], extra_env: Dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    subprocess.run(command, cwd=REPO, env=env, check=True)


def chunk_items(items: Sequence, chunk_size: int) -> List[List]:
    if chunk_size <= 0:
        return [list(items)]
    return [list(items[i : i + chunk_size]) for i in range(0, len(items), chunk_size)]


def select_metadata_batch(
    scope_items: Sequence[Dict[str, object]],
    bad_files: Sequence[Dict[str, object]],
    limit: int,
    exclude_relpaths: set[str] | None = None,
) -> List[Dict[str, object]]:
    exclude_relpaths = exclude_relpaths or set()
    scope_by_relpath = {str(item["relpath"]): item for item in scope_items}
    chosen: List[Dict[str, object]] = []
    for bad in bad_files:
        relpath = str(bad["relpath"])
        errors = set(str(e) for e in bad.get("errors", []))
        if relpath in exclude_relpaths:
            continue
        if not errors or not errors.issubset(ONLY_METADATA_ERRORS):
            continue
        item = scope_by_relpath.get(relpath)
        if item is None:
            continue
        chosen.append(item)
        if len(chosen) >= limit:
            break
    return chosen


def load_translation_cache() -> Dict[str, str]:
    return load_json(TRANSLATION_CACHE_JSON, {})


def save_translation_cache(cache: Dict[str, str]) -> None:
    dump_json(TRANSLATION_CACHE_JSON, cache)


def build_translator() -> Callable[[str], str]:
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source="en", target="zh-CN")
    cache = load_translation_cache()

    def translate(sentence: str) -> str:
        sent = sentence.strip()
        if not sent:
            return ""
        if sent in cache:
            return cache[sent]
        try:
            cache[sent] = translator.translate(sent).strip()
        except Exception:
            cache[sent] = ""
        save_translation_cache(cache)
        return cache[sent]

    return translate


def unique_raw_hits(items: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out: List[Dict[str, str]] = []
    for item in items:
        key = (
            str(item.get("relpath", "")),
            str(item.get("sentence", "")).strip().lower(),
            str(item.get("source", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(item))
    return out


def build_raw_hits_for_item(
    item: Dict[str, object],
    translator: Callable[[str], str],
    fetchers: Sequence[Callable[[str], List[Dict[str, str]]]],
) -> List[Dict[str, str]]:
    word = str(item["word"])
    required_count = int(item.get("required_count") or (3 if str(item.get("word_freq", "")) in {"必备词", "基础词"} else 2))
    hits: List[Dict[str, str]] = []
    for fetcher in fetchers:
        try:
            candidates = fetcher(word)
        except Exception:
            candidates = []
        for cand in candidates:
            if not trusted_entry(cand):
                continue
            hit = {
                "scope_id": str(item["scope_id"]),
                "relpath": str(item["relpath"]),
                "word": word,
                "sentence": str(cand["sentence"]).strip(),
                "translation": translator(str(cand["sentence"]).strip()),
                "tag": str(cand.get("tag", "[例]") or "[例]"),
                "source": str(cand["source"]).strip(),
                "url": str(cand["url"]).strip(),
            }
            if hit["translation"]:
                hits.append(hit)
        hits = unique_raw_hits(hits)
        if len(hits) >= required_count:
            break
    return hits[:required_count]


def append_raw_hits(new_hits: Sequence[Dict[str, str]]) -> None:
    payload = load_json(RAW_HITS_JSON, {"items": []})
    payload["items"] = unique_raw_hits([*payload.get("items", []), *new_hits])
    dump_json(RAW_HITS_JSON, payload)


def run_subset_pipeline(batch_items: Sequence[Dict[str, object]]) -> None:
    backup = work_path("global_corpus_scope.pre_batch200.json")
    shutil.copy2(SCOPE_JSON, backup)
    dump_json(SCOPE_JSON, {"items": list(batch_items)})
    try:
        env = {"P2_BROWSER_HITS_JSON": str(NORMALIZED_HITS_JSON)}
        run_repo_command(["python3", ".trae/scripts/global_corpus_inventory.py"])
        run_repo_command(["python3", ".trae/scripts/global_corpus_fetch.py"], extra_env=env)
        run_repo_command(["python3", ".trae/scripts/global_corpus_apply.py"])
        run_repo_command(["python3", ".trae/scripts/global_corpus_validate.py"])
        run_repo_command(["python3", ".trae/scripts/global_corpus_rebuild_report.py"])
    finally:
        if backup.exists():
            shutil.copy2(backup, SCOPE_JSON)


def main() -> None:
    batch_size = int(os.environ.get("GLOBAL_BATCH_WORDS", "200"))
    chunk_size = int(os.environ.get("GLOBAL_BATCH_CHUNK_SIZE", "25"))
    exclude_relpaths = set()
    scope = load_json(FULL_SCOPE_JSON, {"items": []})
    validate = load_json(VALIDATE_JSON, {"bad_files": []})
    batch_items = select_metadata_batch(scope.get("items", []), validate.get("bad_files", []), batch_size, exclude_relpaths)
    translator = build_translator()
    fetchers = [fetch_oxford, fetch_mw, fetch_cambridge]
    total_raw_hits = 0
    chunks = chunk_items(batch_items, chunk_size)
    for idx, chunk in enumerate(chunks, 1):
        raw_hits: List[Dict[str, str]] = []
        for item in chunk:
            raw_hits.extend(build_raw_hits_for_item(item, translator=translator, fetchers=fetchers))
        append_raw_hits(raw_hits)
        total_raw_hits += len(raw_hits)
        run_repo_command(["python3", ".trae/scripts/global_corpus_browser_normalize.py"])
        run_subset_pipeline(chunk)
        print(f"chunk={idx}/{len(chunks)} items={len(chunk)} raw_hits_added={len(raw_hits)}")
    run_repo_command(["python3", ".trae/scripts/global_corpus_validate.py"])
    run_repo_command(["python3", ".trae/scripts/global_corpus_rebuild_report.py"])
    print(f"batch_items={len(batch_items)}")
    print(f"raw_hits_added={total_raw_hits}")


if __name__ == "__main__":
    main()
