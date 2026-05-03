#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 repair manifest 为问题词条寻找可核验的替换 / 补充例句。

输出：
- /data/user/work/manual_review_candidates.json
- /data/user/work/manual_review_browser_queue.json
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


MANIFEST = Path("/data/user/work/manual_review_manifest.json")
OUT_JSON = Path("/data/user/work/manual_review_candidates.json")
OUT_BROWSER_QUEUE = Path("/data/user/work/manual_review_browser_queue.json")
IN_BROWSER_HITS = Path("/data/user/work/manual_review_browser_hits.json")
EXAM_CACHE = Path("/data/user/work/manual_review_exam_cache.json")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
TIMEOUT = 25
HTML_CACHE: Dict[str, Optional[str]] = {}

EXAM_SOURCES = [
    {
        "name": "考研-2024-英语二",
        "tag": "[真题]",
        "url": "https://mba.upc.edu.cn/_upload/article/files/57/79/5e68df484966be7ad175107d89d7/b7460e64-48ad-4359-888a-05d97d009d57.pdf",
    },
    {
        "name": "考研-2023-英语一",
        "tag": "[真题]",
        "url": "http://gw.xztu.edu.cn/__local/D/8F/1D/8F556EF355DAB6127D7D2D4048F_BD575BBC_DE37A.pdf",
    },
    {
        "name": "考研-2025-英语一",
        "tag": "[真题]",
        "url": "http://tup.tsinghua.edu.cn/upload/books/yz/092796-06.pdf",
    },
]

AUXILIARIES = {
    "am", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did",
    "have", "has", "had",
    "can", "could", "may", "might", "must", "shall", "should", "will", "would",
}


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


def norm_key(s: str) -> str:
    s = normalize_sentence(s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


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
    alts = [re.escape(x) for x in dict.fromkeys(forms) if x]
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


def fetch_html(url: str) -> Optional[str]:
    if url in HTML_CACHE:
        return HTML_CACHE[url]
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            HTML_CACHE[url] = None
            return None
        HTML_CACHE[url] = resp.text
        return resp.text
    except Exception:
        HTML_CACHE[url] = None
        return None


def fetch_pdf_text(url: str) -> str:
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            return ""
        reader = PdfReader(io.BytesIO(resp.content))
        text_parts = []
        for page in reader.pages:
            try:
                text_parts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(text_parts)
    except Exception:
        return ""


def build_exam_cache() -> Dict[str, List[str]]:
    if EXAM_CACHE.exists():
        with EXAM_CACHE.open("r", encoding="utf-8") as f:
            cached = json.load(f)
        return {k: list(v) for k, v in cached.items()}

    exam_map: Dict[str, List[str]] = {}
    for source in EXAM_SOURCES:
        text = fetch_pdf_text(source["url"])
        if not text:
            exam_map[source["name"]] = []
            continue
        exam_map[source["name"]] = split_sentences(text)
        time.sleep(0.1)
    EXAM_CACHE.write_text(json.dumps(exam_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return exam_map


def split_sentences(text: str) -> List[str]:
    text = text.replace("\r", "\n")
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'])", text)
    out: List[str] = []
    for part in parts:
        s = normalize_sentence(part)
        if looks_like_full_sentence(s):
            out.append(s)
    return out


def unique_candidates(items: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out = []
    for item in items:
        k = norm_key(item["sentence"])
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(item)
    return out


def fetch_exam_candidates(word: str, exam_map: Dict[str, List[str]]) -> List[Dict[str, str]]:
    all_hits: List[Dict[str, str]] = []
    for source in EXAM_SOURCES:
        hits = []
        for sentence in exam_map.get(source["name"], []):
            if keep_if_contains_word(word, sentence):
                hits.append(
                    {
                        "sentence": sentence,
                        "tag": source["tag"],
                        "source": source["name"],
                        "url": source["url"],
                        "acquisition_mode": "static",
                    }
                )
        all_hits.extend(hits[:4])
    return unique_candidates(all_hits)


def fetch_cambridge(word: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    urls = [
        f"https://dictionary.cambridge.org/dictionary/english/{quote(word)}",
        f"https://dictionary.cambridge.org/example/english/{quote(word)}",
    ]
    selectors = ["span.eg", "div.eg", "p.eg", ".eg"]
    for url in urls:
        html = fetch_html(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for selector in selectors:
            for node in soup.select(selector):
                s = normalize_sentence(node.get_text(" ", strip=True))
                if s and keep_if_contains_word(word, s) and looks_like_full_sentence(s):
                    out.append(
                        {
                            "sentence": s,
                            "tag": "[例]",
                            "source": "Cambridge",
                            "url": url,
                            "acquisition_mode": "static",
                        }
                    )
        time.sleep(0.05)
    return unique_candidates(out)


def fetch_oxford(word: str) -> List[Dict[str, str]]:
    url = f"https://www.oxfordlearnersdictionaries.com/definition/english/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out: List[Dict[str, str]] = []
    for node in soup.select("span.x, .x, li.x-gs"):
        s = normalize_sentence(node.get_text(" ", strip=True))
        if s and keep_if_contains_word(word, s) and looks_like_full_sentence(s):
            out.append(
                {
                    "sentence": s,
                    "tag": "[例]",
                    "source": "Oxford",
                    "url": url,
                    "acquisition_mode": "static",
                }
            )
    return unique_candidates(out)


def fetch_mw(word: str) -> List[Dict[str, str]]:
    url = f"https://www.merriam-webster.com/dictionary/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out: List[Dict[str, str]] = []
    sec = soup.find(id="examples") or soup
    for node in sec.select("span.t, .t, li .t"):
        s = normalize_sentence(node.get_text(" ", strip=True))
        if s and keep_if_contains_word(word, s) and looks_like_full_sentence(s):
            out.append(
                {
                    "sentence": s,
                    "tag": "[例]",
                    "source": "Merriam-Webster",
                    "url": url,
                    "acquisition_mode": "static",
                }
            )
    return unique_candidates(out)


def load_manifest() -> Dict[str, object]:
    with MANIFEST.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_browser_hits() -> Dict[Tuple[str, str], List[Dict[str, str]]]:
    if not IN_BROWSER_HITS.exists():
        return {}
    obj = json.loads(IN_BROWSER_HITS.read_text(encoding="utf-8"))
    out: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for item in obj.get("items", []):
        key = (str(item.get("scope_id", "")), str(item.get("word", "")))
        out.setdefault(key, []).append(item)
    return out


def hard_issues(issues: List[str]) -> bool:
    return bool(
        {
            "pseudo_placeholder",
            "contains_chinese",
            "missing_target_word",
            "pseudo_fragment",
        }
        & set(issues)
    )


def choose_final_entries(item: Dict[str, object], candidate_pool: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, object]], bool]:
    required_count = int(item["required_count"])
    entries: List[Dict[str, object]] = item["entries"]  # type: ignore[assignment]
    final_entries: List[Dict[str, str]] = []
    replacements: List[Dict[str, object]] = []
    unresolved = False
    used = set()

    def add_candidate(cand: Dict[str, str], reason: str, old_sentence: str = "") -> bool:
        k = norm_key(cand["sentence"])
        if not k or k in used or any(norm_key(x["sentence"]) == k for x in final_entries):
            return False
        used.add(k)
        final_entries.append(cand)
        if old_sentence:
            replacements.append(
                {
                    "old_sentence": old_sentence,
                    "new_sentence": cand["sentence"],
                    "source": cand["source"],
                    "url": cand["url"],
                    "final_tag": cand["tag"],
                    "reason": reason,
                }
            )
        return True

    for entry in entries:
        issues = entry["issues"]
        source = entry["source"]
        sent = entry["sentence"]
        current_tag = entry["tag"] or "[例]"

        exact = None
        for cand in candidate_pool:
            if norm_key(cand["sentence"]) == norm_key(sent):
                exact = cand
                break

        if exact:
            add_candidate(exact, "upgrade_existing", old_sentence=sent)
            continue

        if source != "Unknown" and not hard_issues(issues):
            add_candidate(
                {
                    "sentence": sent,
                    "tag": current_tag,
                    "source": source,
                    "url": entry["url"],
                    "acquisition_mode": "existing",
                },
                "keep_existing",
            )
            continue

        if hard_issues(issues) or source == "Unknown" or "manual_review_reported" in issues:
            replaced = False
            for cand in candidate_pool:
                if add_candidate(cand, "replace_problem_entry", old_sentence=sent):
                    replaced = True
                    break
            if not replaced:
                if not hard_issues(issues):
                    add_candidate(
                        {
                            "sentence": sent,
                            "tag": current_tag,
                            "source": source,
                            "url": entry["url"],
                            "acquisition_mode": "existing",
                        },
                        "retain_unresolved",
                    )
                unresolved = True
            continue

        add_candidate(
            {
                "sentence": sent,
                "tag": current_tag,
                "source": source,
                "url": entry["url"],
                "acquisition_mode": "existing",
            },
            "keep_existing",
        )

    for cand in candidate_pool:
        if len(final_entries) >= required_count:
            break
        add_candidate(cand, "top_up")

    if len(final_entries) < required_count:
        unresolved = True

    return final_entries, replacements, unresolved


def run_for_items(items: List[Dict[str, object]], target_group: str = "all", target_scope: str = "") -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    exam_map = build_exam_cache()
    browser_hits = load_browser_hits()

    results: List[Dict[str, object]] = []
    browser_queue: List[Dict[str, object]] = []

    for item in items:
        if target_group != "all" and item.get("group") != target_group:
            continue
        if target_scope and item.get("scope_id") != target_scope:
            continue
        word_issues = item["word_issues"]
        entries = item["entries"]
        if not word_issues and not any(e["issues"] for e in entries):
            continue

        word = item["word"]
        scope_id = item["scope_id"]
        exam_hits = fetch_exam_candidates(word, exam_map)
        is_early = item.get("group") == "early"
        needs_full_fetch = bool(
            {
                "has_placeholder",
                "has_fragment",
                "count_insufficient",
                "manual_review_reported",
                "missing_corpus_block",
            }
            & set(word_issues)
        )
        if is_early and not needs_full_fetch:
            needs_full_fetch = False
        if needs_full_fetch:
            cam_hits = fetch_cambridge(word)
            ox_hits = fetch_oxford(word)
            mw_hits = fetch_mw(word)
        else:
            cam_hits = fetch_cambridge(word)
            ox_hits = []
            mw_hits = []

        browser_pool = browser_hits.get((scope_id, word), [])
        candidate_pool = unique_candidates(exam_hits + cam_hits + ox_hits + mw_hits + browser_pool)
        final_entries, replacements, unresolved = choose_final_entries(item, candidate_pool)

        unresolved_reasons = []
        if unresolved:
            unresolved_reasons.append("static_candidates_insufficient")
        if not candidate_pool:
            unresolved_reasons.append("static_no_hits")

        result_item = {
            "scope_id": scope_id,
            "batch_id": item["batch_id"],
            "group": item.get("group"),
            "relpath": item["relpath"],
            "word": word,
            "word_freq": item["word_freq"],
            "required_count": item["required_count"],
            "current_count": item["current_count"],
            "final_entries": final_entries,
            "replacements": replacements,
            "candidate_count": len(candidate_pool),
            "candidate_sources": {
                "exam": len(exam_hits),
                "cambridge": len(cam_hits),
                "oxford": len(ox_hits),
                "merriam_webster": len(mw_hits),
                "browser": len(browser_pool),
            },
            "word_issues": word_issues,
            "unresolved": unresolved,
            "unresolved_reasons": unresolved_reasons,
        }
        results.append(result_item)

        if unresolved:
            browser_queue.append(
                {
                    "scope_id": scope_id,
                    "batch_id": item["batch_id"],
                    "relpath": item["relpath"],
                    "word": word,
                    "reasons": unresolved_reasons,
                    "needs_full_fetch": needs_full_fetch,
                    "urls": [
                        f"https://dictionary.cambridge.org/dictionary/english/{quote(word)}",
                        f"https://dictionary.cambridge.org/example/english/{quote(word)}",
                        f"https://www.oxfordlearnersdictionaries.com/definition/english/{quote(word)}",
                        f"https://www.merriam-webster.com/dictionary/{quote(word)}",
                    ],
                }
            )
    return results, browser_queue


def main() -> None:
    manifest = load_manifest()
    items: List[Dict[str, object]] = manifest["items"]  # type: ignore[assignment]
    target_group = sys.argv[1] if len(sys.argv) > 1 else "all"
    target_scope = sys.argv[2] if len(sys.argv) > 2 else ""
    results, browser_queue = run_for_items(items, target_group=target_group, target_scope=target_scope)

    OUT_JSON.write_text(
        json.dumps(
            {
                "problem_items": len(results),
                "items": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    OUT_BROWSER_QUEUE.write_text(
        json.dumps({"items": browser_queue}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    unresolved_n = sum(1 for x in results if x["unresolved"])
    exam_n = sum(1 for x in results if x["candidate_sources"]["exam"] > 0)
    print(f"problem_items={len(results)}")
    print(f"exam_hit_words={exam_n}")
    print(f"unresolved_words={unresolved_n}")
    print(f"json={OUT_JSON}")
    print(f"browser_queue={OUT_BROWSER_QUEUE}")


if __name__ == "__main__":
    main()
