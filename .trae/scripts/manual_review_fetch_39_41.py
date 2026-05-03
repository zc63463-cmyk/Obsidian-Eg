#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第39-41批人工复核专用保守抓取：
- 输入：/data/user/work/manual_review_manifest_39_41.json
- 输出：
  - /data/user/work/manual_review_candidates_39_41.json
  - /data/user/work/manual_review_browser_queue_39_41.json

约束：
- 保留已知可核验句；
- Unknown / NoSource 不得进入 final_entries；
- 不足2条则 unresolved，不进入 apply。
"""

from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


MANIFEST = Path("/data/user/work/manual_review_manifest_39_41.json")
OUT_JSON = Path("/data/user/work/manual_review_candidates_39_41.json")
OUT_BROWSER_QUEUE = Path("/data/user/work/manual_review_browser_queue_39_41.json")
IN_BROWSER_HITS = Path("/data/user/work/manual_review_browser_hits_39_41.json")
EXAM_CACHE = Path("/data/user/work/manual_review_exam_cache_39_41.json")

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
        if base.endswith("e"):
            forms.update({base + "d", base[:-1] + "ing"})
        else:
            forms.update({base + "ed", base + "ing"})
        if last in consonants and not base.endswith("e"):
            forms.update({base + last + "ed", base + last + "ing"})
    alts = [re.escape(x) for x in sorted(forms)]
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


def trusted_entry(entry: Dict[str, str]) -> bool:
    source = (entry.get("source") or "").strip()
    sentence = normalize_sentence(entry.get("sentence", ""))
    url = (entry.get("url") or "").strip()
    if source in {"Unknown", "NoSource", ""}:
        return False
    if not sentence or not looks_like_full_sentence(sentence):
        return False
    if source.startswith("考研-"):
        return bool(url)
    return bool(url and source in {"Cambridge", "Oxford", "Merriam-Webster", "Browser"})


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
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(parts)
    except Exception:
        return ""


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


def build_exam_cache() -> Dict[str, List[str]]:
    if EXAM_CACHE.exists():
        return json.loads(EXAM_CACHE.read_text(encoding="utf-8"))
    exam_map: Dict[str, List[str]] = {}
    for source in EXAM_SOURCES:
        text = fetch_pdf_text(source["url"])
        exam_map[source["name"]] = split_sentences(text) if text else []
        time.sleep(0.1)
    EXAM_CACHE.write_text(json.dumps(exam_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return exam_map


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
    for url in urls:
        html = fetch_html(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for node in soup.select("span.eg, div.eg, p.eg, .eg"):
            s = normalize_sentence(node.get_text(" ", strip=True))
            if s and keep_if_contains_word(word, s) and looks_like_full_sentence(s):
                out.append({"sentence": s, "tag": "[例]", "source": "Cambridge", "url": url, "acquisition_mode": "static"})
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
            out.append({"sentence": s, "tag": "[例]", "source": "Oxford", "url": url, "acquisition_mode": "static"})
    return unique_candidates(out)


def fetch_mw(word: str) -> List[Dict[str, str]]:
    url = f"https://www.merriam-webster.com/dictionary/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    sec = soup.find(id="examples") or soup
    out: List[Dict[str, str]] = []
    for node in sec.select("span.t, .t, li .t"):
        s = normalize_sentence(node.get_text(" ", strip=True))
        if s and keep_if_contains_word(word, s) and looks_like_full_sentence(s):
            out.append({"sentence": s, "tag": "[例]", "source": "Merriam-Webster", "url": url, "acquisition_mode": "static"})
    return unique_candidates(out)


def load_manifest() -> Dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def load_browser_hits() -> Dict[str, List[Dict[str, str]]]:
    if not IN_BROWSER_HITS.exists():
        return {}
    obj = json.loads(IN_BROWSER_HITS.read_text(encoding="utf-8"))
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for item in obj.get("items", []):
        grouped.setdefault(str(item.get("word", "")), []).append(item)
    return grouped


def choose_final_entries_strict(item: Dict[str, object], candidate_pool: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, object]], bool]:
    required_count = int(item["required_count"])
    entries: List[Dict[str, object]] = item["entries"]  # type: ignore[assignment]
    final_entries: List[Dict[str, str]] = []
    replacements: List[Dict[str, object]] = []
    used = set()

    def add_candidate(cand: Dict[str, str], reason: str, old_sentence: str = "") -> bool:
        if not trusted_entry(cand):
            return False
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
        current = {
            "sentence": normalize_sentence(str(entry.get("sentence", ""))),
            "tag": str(entry.get("tag", "[例]") or "[例]"),
            "source": str(entry.get("source", "")),
            "url": str(entry.get("url", "")),
            "acquisition_mode": str(entry.get("acquisition_mode", "existing") or "existing"),
        }
        if trusted_entry(current):
            add_candidate(current, "keep_existing")

    for cand in candidate_pool:
        if len(final_entries) >= required_count:
            break
        add_candidate(cand, "top_up")

    unresolved = len(final_entries) < required_count
    return final_entries, replacements, unresolved


def main() -> None:
    manifest = load_manifest()
    items: List[Dict[str, object]] = manifest["items"]  # type: ignore[assignment]
    exam_map = build_exam_cache()
    browser_hits = load_browser_hits()

    results: List[Dict[str, object]] = []
    browser_queue: List[Dict[str, object]] = []

    for item in items:
        word = str(item["word"])
        exam_hits = fetch_exam_candidates(word, exam_map)
        cam_hits = fetch_cambridge(word)
        ox_hits = fetch_oxford(word)
        mw_hits = fetch_mw(word)
        browser_pool = browser_hits.get(word, [])
        candidate_pool = unique_candidates(exam_hits + cam_hits + ox_hits + mw_hits + browser_pool)
        final_entries, replacements, unresolved = choose_final_entries_strict(item, candidate_pool)

        result_item = {
            "scope_id": item["scope_id"],
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
            "word_issues": item.get("word_issues", []),
            "unresolved": unresolved,
            "unresolved_reasons": ["strict_verified_candidates_insufficient"] if unresolved else [],
        }
        results.append(result_item)

        if unresolved:
            browser_queue.append(
                {
                    "scope_id": item["scope_id"],
                    "batch_id": item["batch_id"],
                    "relpath": item["relpath"],
                    "word": word,
                    "reasons": ["strict_verified_candidates_insufficient"],
                    "urls": [
                        f"https://dictionary.cambridge.org/dictionary/english/{quote(word)}",
                        f"https://dictionary.cambridge.org/example/english/{quote(word)}",
                        f"https://www.oxfordlearnersdictionaries.com/definition/english/{quote(word)}",
                        f"https://www.merriam-webster.com/dictionary/{quote(word)}",
                    ],
                }
            )

    OUT_JSON.write_text(json.dumps({"problem_items": len(results), "items": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_BROWSER_QUEUE.write_text(json.dumps({"items": browser_queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"problem_items={len(results)}")
    print(f"unresolved_words={sum(1 for x in results if x['unresolved'])}")
    print(f"json={OUT_JSON}")
    print(f"browser_queue={OUT_BROWSER_QUEUE}")


if __name__ == "__main__":
    main()
