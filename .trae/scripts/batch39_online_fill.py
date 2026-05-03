#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第39批（L0_超纲词 第9批：801–900）联网补齐语料：
- 输入：/data/user/work/batch39_needs_online.tsv
- 输出：
  - /data/user/work/batch39_static_candidates.json
  - /data/user/work/batch39_browser_queue.json
- 来源优先级：考研真题静态匹配 -> Cambridge -> Oxford -> Merriam-Webster
- 禁止写入 NoSource/伪例句；静态不足时仅排入 browser queue
"""

from __future__ import annotations

import io
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from batch39_validate import keep_if_contains_word, looks_like_full_sentence, strip_tag


REPO = Path("/workspace/Obsidian-Eg")
NEEDS_ONLINE = Path("/data/user/work/batch39_needs_online.tsv")
APPLY_STATS = Path("/data/user/work/batch39_apply_stats.json")
REPORT_PATH = REPO / ".trae" / "reports" / "第39批次超纲词801-900_6.5-6.6_处理报告.md"
BATCH_LIST = REPO / ".trae" / "batches" / "batch39_files.txt"
OUT_CANDIDATES = Path("/data/user/work/batch39_static_candidates.json")
OUT_BROWSER_QUEUE = Path("/data/user/work/batch39_browser_queue.json")
EXAM_CACHE = Path("/data/user/work/batch39_exam_cache.json")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
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


@dataclass
class Candidate:
    relpath: str
    word: str
    sentence: str
    tag: str
    source: str
    url: str
    acquisition_mode: str


def read_text(p: Path) -> str:
    with p.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def write_text(p: Path, text: str) -> None:
    with p.open("w", encoding="utf-8", newline="") as f:
        f.write(text)


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


def sent_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def fetch_html(url: str) -> Optional[str]:
    if url in HTML_CACHE:
        return HTML_CACHE[url]
    try:
        r = SESSION.get(url, timeout=25)
        if r.status_code != 200:
            HTML_CACHE[url] = None
            return None
        HTML_CACHE[url] = r.text
        return r.text
    except Exception:
        HTML_CACHE[url] = None
        return None


def fetch_pdf_text(url: str) -> str:
    try:
        r = SESSION.get(url, timeout=25)
        if r.status_code != 200:
            return ""
        reader = PdfReader(io.BytesIO(r.content))
        parts: List[str] = []
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
    cache: Dict[str, List[str]] = {}
    for source in EXAM_SOURCES:
        text = fetch_pdf_text(source["url"])
        cache[source["name"]] = split_sentences(text) if text else []
        time.sleep(0.1)
    EXAM_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cache


def unique_candidates(items: Iterable[Candidate]) -> List[Candidate]:
    seen = set()
    out: List[Candidate] = []
    for item in items:
        key = (item.relpath, item.word, sent_key(item.sentence))
        if not key[2] or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def fetch_exam_candidates(relpath: str, word: str, exam_map: Dict[str, List[str]]) -> List[Candidate]:
    out: List[Candidate] = []
    for source in EXAM_SOURCES:
        for sentence in exam_map.get(source["name"], []):
            if keep_if_contains_word(word, sentence):
                out.append(
                    Candidate(
                        relpath=relpath,
                        word=word,
                        sentence=sentence,
                        tag=source["tag"],
                        source=source["name"],
                        url=source["url"],
                        acquisition_mode="static",
                    )
                )
    return unique_candidates(out)


def fetch_cambridge(relpath: str, word: str) -> List[Candidate]:
    url = f"https://dictionary.cambridge.org/dictionary/english/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out: List[Candidate] = []
    for sp in soup.select("span.eg"):
        sentence = normalize_sentence(sp.get_text(" ", strip=True))
        if sentence and keep_if_contains_word(word, sentence) and looks_like_full_sentence(sentence):
            out.append(Candidate(relpath, word, sentence, "[例]", "Cambridge", url, "static"))
    return unique_candidates(out)


def fetch_oxford(relpath: str, word: str) -> List[Candidate]:
    url = f"https://www.oxfordlearnersdictionaries.com/definition/english/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out: List[Candidate] = []
    for sp in soup.select("span.x"):
        sentence = normalize_sentence(sp.get_text(" ", strip=True))
        if sentence and keep_if_contains_word(word, sentence) and looks_like_full_sentence(sentence):
            out.append(Candidate(relpath, word, sentence, "[例]", "Oxford", url, "static"))
    return unique_candidates(out)


def fetch_mw(relpath: str, word: str) -> List[Candidate]:
    url = f"https://www.merriam-webster.com/dictionary/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    sec = soup.find(id="examples")
    if not sec:
        return []
    out: List[Candidate] = []
    for sp in sec.select("span.t"):
        sentence = normalize_sentence(sp.get_text(" ", strip=True))
        if sentence and keep_if_contains_word(word, sentence) and looks_like_full_sentence(sentence):
            out.append(Candidate(relpath, word, sentence, "[例]", "Merriam-Webster", url, "static"))
    return unique_candidates(out)


def corpus_block_span(text: str) -> Optional[Tuple[int, int]]:
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
    return start, pos


def parse_corpus_bullets(block: str) -> List[str]:
    out: List[str] = []
    for ln in block.splitlines():
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if m:
            out.append(m.group(1).rstrip())
    return out


def load_needs() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not NEEDS_ONLINE.exists():
        return rows
    lines = [ln.rstrip("\n") for ln in NEEDS_ONLINE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for ln in lines[1:]:
        parts = ln.split("\t")
        if len(parts) != 6:
            continue
        relpath, word, word_freq, required, have, missing = parts
        if int(missing) <= 0:
            continue
        rows.append(
            {
                "relpath": relpath,
                "word": word,
                "word_freq": word_freq,
                "required": required,
                "have": have,
                "missing": missing,
            }
        )
    return rows


def keep_existing_bullets(word: str, bullets: List[str]) -> Tuple[List[str], set[str]]:
    kept: List[str] = []
    seen: set[str] = set()
    for raw in bullets:
        sentence, tag = strip_tag(raw)
        sentence = normalize_sentence(sentence)
        if not sentence:
            continue
        if not keep_if_contains_word(word, sentence):
            continue
        if not looks_like_full_sentence(sentence):
            continue
        key = sent_key(sentence)
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(f"{sentence} `{tag or '[例]'}`")
    return kept, seen


def append_examples_to_file(
    relpath: str,
    word: str,
    missing: int,
    exam_map: Dict[str, List[str]],
) -> Tuple[List[Candidate], List[Candidate], Optional[Dict[str, object]], List[str]]:
    path = REPO / relpath
    text = read_text(path)
    span = corpus_block_span(text)
    if not span:
        return [], [], None, [f"{relpath}: 缺少语料callout"]
    start, end = span
    block = text[start:end]
    bullets = parse_corpus_bullets(block)
    kept_bullets, existing_keys = keep_existing_bullets(word, bullets)

    static_pool = unique_candidates(
        fetch_exam_candidates(relpath, word, exam_map)
        + fetch_cambridge(relpath, word)
        + fetch_oxford(relpath, word)
        + fetch_mw(relpath, word)
    )

    added: List[Candidate] = []
    for cand in static_pool:
        if len(added) >= missing:
            break
        key = sent_key(cand.sentence)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        added.append(cand)

    queue_item: Optional[Dict[str, object]] = None
    errors: List[str] = []
    if len(added) < missing:
        queue_item = {
            "relpath": relpath,
            "word": word,
            "missing": missing - len(added),
            "urls": [source["url"] for source in EXAM_SOURCES] + [
                f"https://dictionary.cambridge.org/dictionary/english/{quote(word)}",
                f"https://www.oxfordlearnersdictionaries.com/definition/english/{quote(word)}",
                f"https://www.merriam-webster.com/dictionary/{quote(word)}",
            ],
        }
        errors.append(f"{word}: 静态来源不足，已加入 browser queue")

    lines = block.splitlines()
    out_lines: List[str] = []
    header_done = False
    for ln in lines:
        if not header_done:
            out_lines.append(ln)
            if re.match(r"^>[ \t]*\[!example\]-[ \t]*语料", ln):
                header_done = True
            continue
        if re.match(r"^>\s*-\s+", ln):
            continue
        out_lines.append(ln)

    for bullet in kept_bullets:
        out_lines.append(f"> - {bullet}")
    for cand in added:
        out_lines.append(f"> - {cand.sentence} `{cand.tag}`")

    new_block = "\n".join(out_lines) + ("\n" if block.endswith("\n") else "")
    new_text = text[:start] + new_block + text[end:]
    if new_text != text:
        write_text(path, new_text)

    return static_pool, added, queue_item, errors


def write_report(
    apply_stats: Dict[str, object],
    added_examples: List[Candidate],
    queue_items: List[Dict[str, object]],
    errors: List[str],
) -> None:
    rels = [ln.strip() for ln in BATCH_LIST.read_text(encoding="utf-8").splitlines() if ln.strip()]
    first = Path(rels[0]).name if rels else ""
    last = Path(rels[-1]).name if rels else ""
    by_source: Dict[str, int] = {}
    for cand in added_examples:
        by_source[cand.source] = by_source.get(cand.source, 0) + 1

    lines: List[str] = []
    lines.append("# 第39批次超纲词801-900 6.5/6.6 处理报告")
    lines.append("")
    lines.append("## 批次范围")
    lines.append("- 目录：`Wiki/L0_超纲词/`")
    lines.append("- 排序口径：Python `sorted()` 按文件名")
    lines.append("- 切片：`files[800:900]`（共100个）")
    if first and last:
        lines.append(f"- 首尾：`{first}` ~ `{last}`")
    lines.append("")
    lines.append("## 处理统计（离线 apply）")
    for k in ["files_total", "6.5_changed", "6.5_skipped", "6.6_changed", "6.6_skipped", "needs_online_files", "needs_online_sentences"]:
        if k in apply_stats:
            lines.append(f"- {k}: {apply_stats[k]}")
    lines.append("")
    lines.append("## 静态联网补齐统计")
    lines.append(f"- 本批静态新增语料条数：{len(added_examples)}")
    lines.append(f"- browser queue 词条数：{len(queue_items)}")
    if by_source:
        lines.append("- 来源分布：")
        for src, n in sorted(by_source.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"  - {src}: {n}")
    lines.append("")
    lines.append("## 异常/人工复核")
    if errors:
        for e in errors[:300]:
            lines.append(f"- {e}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 联网证据表（静态阶段）")
    lines.append("")
    lines.append("| word | sentence | tag | source | url | acquisition_mode |")
    lines.append("|---|---|---|---|---|---|")
    for cand in added_examples:
        sent = cand.sentence.replace("|", "\\|")
        url = cand.url.replace("|", "\\|")
        lines.append(f"| {cand.word} | {sent} | {cand.tag} | {cand.source} | {url} | {cand.acquisition_mode} |")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    needs = load_needs()
    apply_stats: Dict[str, object] = {}
    if APPLY_STATS.exists():
        apply_stats = json.loads(APPLY_STATS.read_text(encoding="utf-8"))

    exam_map = build_exam_cache()
    candidates_all: List[Dict[str, object]] = []
    added_all: List[Candidate] = []
    queue_all: List[Dict[str, object]] = []
    errors_all: List[str] = []

    for row in needs:
        static_pool, added, queue_item, errors = append_examples_to_file(
            row["relpath"], row["word"], int(row["missing"]), exam_map
        )
        candidates_all.extend(asdict(c) for c in static_pool)
        added_all.extend(added)
        if queue_item:
            queue_all.append(queue_item)
        errors_all.extend(errors)
        time.sleep(0.2)

    OUT_CANDIDATES.write_text(
        json.dumps({"items": candidates_all}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_BROWSER_QUEUE.write_text(
        json.dumps({"items": queue_all}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_report(apply_stats, added_all, queue_all, errors_all)
    print(f"needs_files={len(needs)} added_sentences={len(added_all)} queue={len(queue_all)}")
    print(f"candidates -> {OUT_CANDIDATES}")
    print(f"browser_queue -> {OUT_BROWSER_QUEUE}")
    print(f"report -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
