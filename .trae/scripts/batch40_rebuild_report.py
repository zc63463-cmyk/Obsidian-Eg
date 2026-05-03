#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建第40批最终报告：
- 扫描 `.trae/batches/batch40_files.txt` 清单内每个词条的 `> [!example]- 语料`
- 优先使用静态候选池 / browser hits 元数据恢复来源
- 元数据缺失时再回退到 Cambridge/Oxford/MW 规范化匹配
- 保留最终 tag，不强制降级为 `[例]`
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from batch40_validate import VALID_TAG_RE


REPO = Path("/workspace/Obsidian-Eg")
BATCH_LIST = REPO / ".trae" / "batches" / "batch40_files.txt"
REPORT_PATH = REPO / ".trae" / "reports" / "第40批次超纲词901-1000_6.5-6.6_处理报告.md"
APPLY_STATS_PATH = Path("/data/user/work/batch40_apply_stats.json")
STATIC_CANDIDATES_PATH = Path("/data/user/work/batch40_static_candidates.json")
BROWSER_HITS_PATH = Path("/data/user/work/batch40_browser_hits.json")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
SESSION.timeout = 25

def read_text(p: Path) -> str:
    with p.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def normalize_sentence(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
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


def fetch_html(url: str) -> Optional[str]:
    try:
        r = SESSION.get(url)
        if r.status_code != 200:
            return None
        return r.text
    except Exception:
        return None


def fetch_cambridge_examples(word: str) -> Tuple[str, Dict[str, str]]:
    url = f"https://dictionary.cambridge.org/dictionary/english/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return url, {}
    soup = BeautifulSoup(html, "html.parser")
    m: Dict[str, str] = {}
    for sp in soup.select("span.eg"):
        t = sp.get_text(" ", strip=True)
        k = norm_key(t)
        if k and k not in m:
            m[k] = normalize_sentence(t)
    return url, m


def fetch_oxford_examples(word: str) -> Tuple[str, Dict[str, str]]:
    url = f"https://www.oxfordlearnersdictionaries.com/definition/english/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return url, {}
    soup = BeautifulSoup(html, "html.parser")
    m: Dict[str, str] = {}
    for sp in soup.select("span.x"):
        t = sp.get_text(" ", strip=True)
        k = norm_key(t)
        if k and k not in m:
            m[k] = normalize_sentence(t)
    return url, m


def fetch_mw_examples(word: str) -> Tuple[str, Dict[str, str]]:
    url = f"https://www.merriam-webster.com/dictionary/{quote(word)}"
    html = fetch_html(url)
    if not html:
        return url, {}
    soup = BeautifulSoup(html, "html.parser")
    sec = soup.find(id="examples")
    if not sec:
        return url, {}
    m: Dict[str, str] = {}
    for sp in sec.select("span.t"):
        t = sp.get_text(" ", strip=True)
        k = norm_key(t)
        if k and k not in m:
            m[k] = normalize_sentence(t)
    return url, m


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


def parse_corpus_lines(block: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for ln in block.splitlines():
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if not m:
            continue
        raw = m.group(1).rstrip()
        tag = "[例]"
        mtag = VALID_TAG_RE.search(raw)
        if mtag:
            tag = mtag.group(0).strip("`")
            raw = VALID_TAG_RE.sub("", raw).rstrip()
        else:
            raw = re.sub(r"`\[[^\]]+\]`\s*$", "", raw).rstrip()
        sent = normalize_sentence(raw)
        if sent:
            out.append((sent, tag))
    return out


@dataclass
class EvidenceRow:
    word: str
    old_sentence: str
    new_sentence: str
    final_tag: str
    source: str
    url: str
    acquisition_mode: str
    issue_type: str


def load_metadata() -> Dict[Tuple[str, str], Dict[str, str]]:
    out: Dict[Tuple[str, str], Dict[str, str]] = {}
    for path in [STATIC_CANDIDATES_PATH, BROWSER_HITS_PATH]:
        if not path.exists():
            continue
        obj = json.loads(path.read_text(encoding="utf-8"))
        for item in obj.get("items", []):
            word = str(item.get("word", "")).strip()
            sentence = normalize_sentence(str(item.get("sentence", "")))
            key = (word, norm_key(sentence))
            if not word or not key[1]:
                continue
            out[key] = {
                "source": str(item.get("source", "")),
                "url": str(item.get("url", "")),
                "acquisition_mode": str(item.get("acquisition_mode", "")) or ("browser" if path == BROWSER_HITS_PATH else "static"),
            }
    return out


def main() -> None:
    rels = [ln.strip() for ln in BATCH_LIST.read_text(encoding="utf-8").splitlines() if ln.strip()]
    first = Path(rels[0]).name if rels else ""
    last = Path(rels[-1]).name if rels else ""
    metadata = load_metadata()

    apply_stats: Dict[str, object] = {}
    if APPLY_STATS_PATH.exists():
        apply_stats = json.loads(APPLY_STATS_PATH.read_text(encoding="utf-8"))

    rows: List[EvidenceRow] = []
    by_source: Dict[str, int] = {}
    anomalies: List[str] = []

    for rel in rels:
        word = Path(rel).stem
        text = read_text(REPO / rel)
        block = corpus_block(text)
        corpus = parse_corpus_lines(block)
        if not corpus:
            continue

        cam_url, cam_map = fetch_cambridge_examples(word)
        time.sleep(0.05)
        ox_url, ox_map = fetch_oxford_examples(word)
        time.sleep(0.05)
        mw_url, mw_map = fetch_mw_examples(word)
        time.sleep(0.05)

        for sent, tag in corpus:
            k = norm_key(sent)
            meta = metadata.get((word, k))
            if meta:
                src = meta.get("source", "Unknown")
                url = meta.get("url", "")
                acquisition_mode = meta.get("acquisition_mode", "static")
                issue_type = "metadata"
            elif k in cam_map:
                src, url, acquisition_mode, issue_type = "Cambridge", cam_url, "static", "dictionary_match"
            elif k in ox_map:
                src, url, acquisition_mode, issue_type = "Oxford", ox_url, "static", "dictionary_match"
            elif k in mw_map:
                src, url, acquisition_mode, issue_type = "Merriam-Webster", mw_url, "static", "dictionary_match"
            elif tag.startswith("[真题]") or tag.startswith("[考研-"):
                src, url, acquisition_mode, issue_type = "Unknown-Exam", "", "unknown", "unmatched_exam"
                anomalies.append(f"{word}: 真题语料未在元数据或词典匹配到，请补录来源")
            else:
                src, url, acquisition_mode, issue_type = "Unknown", "", "unknown", "unmatched"
                anomalies.append(f"{word}: 语料未在 Cambridge/Oxford/MW 匹配到，请人工复核")
            by_source[src] = by_source.get(src, 0) + 1
            rows.append(
                EvidenceRow(
                    word=word,
                    old_sentence="",
                    new_sentence=sent,
                    final_tag=tag,
                    source=src,
                    url=url,
                    acquisition_mode=acquisition_mode,
                    issue_type=issue_type,
                )
            )

    lines: List[str] = []
    lines.append("# 第40批次超纲词901-1000 6.5/6.6 处理报告")
    lines.append("")
    lines.append("## 批次范围")
    lines.append("- 目录：`Wiki/L0_超纲词/`")
    lines.append("- 排序口径：Python `sorted()` 按文件名")
    lines.append("- 切片：`files[900:1000]`（共100个）")
    if first and last:
        lines.append(f"- 首尾：`{first}` ~ `{last}`")
    lines.append("")
    lines.append("## 处理统计（离线 apply）")
    for k in ["files_total", "6.5_changed", "6.5_skipped", "6.6_changed", "6.6_skipped", "needs_online_files", "needs_online_sentences"]:
        if k in apply_stats:
            lines.append(f"- {k}: {apply_stats[k]}")
    lines.append("")
    lines.append("## 异常/人工复核")
    if anomalies:
        for a in anomalies:
            lines.append(f"- {a}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 联网证据表（仅报告留存，不写回词条）")
    lines.append("")
    lines.append(f"- 证据行总数：{len(rows)}")
    if by_source:
        lines.append("- 来源分布：")
        for src, n in sorted(by_source.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"  - {src}: {n}")
    lines.append("")
    lines.append("| word | old_sentence | new_sentence | final_tag | source | url | acquisition_mode | issue_type |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        old_sent = r.old_sentence.replace("|", "\\|")
        sent = r.new_sentence.replace("|", "\\|")
        url = r.url.replace("|", "\\|")
        lines.append(
            f"| {r.word} | {old_sent} | {sent} | {r.final_tag} | {r.source} | {url} | {r.acquisition_mode} | {r.issue_type} |"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote report -> {REPORT_PATH} rows={len(rows)}")


if __name__ == "__main__":
    main()
