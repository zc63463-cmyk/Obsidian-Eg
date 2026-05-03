#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从第39-41批处理报告生成本轮人工复核专用 manifest。

输出：
- /data/user/work/manual_review_manifest_39_41.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


REPO = Path("/workspace/Obsidian-Eg")
REPORTS = [
    REPO / ".trae" / "reports" / "第39批次超纲词801-900_6.5-6.6_处理报告.md",
    REPO / ".trae" / "reports" / "第40批次超纲词901-1000_6.5-6.6_处理报告.md",
    REPO / ".trae" / "reports" / "第41批次超纲词1001-1050_6.5-6.6_处理报告.md",
]
LIST_FILES = [
    REPO / ".trae" / "batches" / "batch39_files.txt",
    REPO / ".trae" / "batches" / "batch40_files.txt",
    REPO / ".trae" / "batches" / "batch41_files.txt",
]
OUT = Path("/data/user/work/manual_review_manifest_39_41.json")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def norm_sentence(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    s = s.strip('"\'“”‘’')
    return s.rstrip(".?!")


def load_relpaths() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for list_file in LIST_FILES:
        for rel in [ln.strip() for ln in read_text(list_file).splitlines() if ln.strip()]:
            out[Path(rel).stem] = rel
    return out


def parse_anomaly_words(text: str) -> List[str]:
    out: List[str] = []
    m = re.search(r"## 异常/人工复核\s*\n(.*?)(?:\n## |\Z)", text, flags=re.S)
    if not m:
        return out
    for line in m.group(1).splitlines():
        mm = re.match(r"-\s+([^:]+):\s+语料未在 Cambridge/Oxford/MW 匹配到，请人工复核", line.strip())
        if mm:
            out.append(mm.group(1).strip())
    return out


def parse_evidence_rows(text: str) -> Dict[str, List[Dict[str, str]]]:
    rows: Dict[str, List[Dict[str, str]]] = {}
    in_table = False
    for line in text.splitlines():
        if line.startswith("| word |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        if line.startswith("|---|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 8:
            continue
        word, old_sentence, new_sentence, final_tag, source, url, acquisition_mode, issue_type = parts[:8]
        rows.setdefault(word, []).append(
            {
                "old_sentence": old_sentence,
                "sentence": new_sentence,
                "tag": final_tag,
                "source": source,
                "url": url,
                "acquisition_mode": acquisition_mode,
                "issue_type": issue_type,
            }
        )
    return rows


def current_entries_from_file(relpath: str) -> List[Dict[str, str]]:
    text = read_text(REPO / relpath)
    m = re.search(r"(?m)^>[ \t]*\[!example\]-[ \t]*语料(?:[ \t].*)?\r?\n", text)
    if not m:
        return []
    pos = m.end()
    out: List[Dict[str, str]] = []
    while pos < len(text):
        line_end = text.find("\n", pos)
        if line_end == -1:
            line_end = len(text)
        line = text[pos:line_end]
        if not line.startswith(">"):
            break
        mm = re.match(r"^>\s*-\s+(.*?)(?:\s+`(\[[^\]]+\])`)?\s*$", line)
        if mm:
            out.append({"sentence": mm.group(1).strip(), "tag": mm.group(2) or "[例]"})
        pos = line_end + 1
    return out


def main() -> None:
    relpaths = load_relpaths()
    all_words: Dict[str, Dict[str, object]] = {}

    for report in REPORTS:
        text = read_text(report)
        anomaly_words = parse_anomaly_words(text)
        evidence = parse_evidence_rows(text)
        batch_match = re.search(r"第(\d+)批次", report.name)
        scope_id = f"batch{batch_match.group(1)}" if batch_match else report.stem

        for word in sorted(set(anomaly_words)):
            relpath = relpaths.get(word)
            if not relpath:
                continue
            rows = evidence.get(word, [])
            known_good_entries = []
            unknown_entries = []
            for row in rows:
                entry = {
                    "sentence": row["sentence"],
                    "tag": row["tag"] or "[例]",
                    "source": row["source"],
                    "url": row["url"],
                    "acquisition_mode": row["acquisition_mode"],
                    "issues": ["manual_review_reported"] + (["unknown_source"] if row["source"] == "Unknown" else []),
                }
                if row["source"] == "Unknown":
                    unknown_entries.append(entry)
                else:
                    known_good_entries.append(entry)

            all_words[word] = {
                "scope_id": scope_id,
                "batch_id": batch_match.group(1) if batch_match else "",
                "group": "39-41-review",
                "relpath": relpath,
                "word": word,
                "word_freq": "超纲词",
                "required_count": 2,
                "current_entries": current_entries_from_file(relpath),
                "known_good_entries": known_good_entries,
                "unknown_entries": unknown_entries,
                "entries": known_good_entries + unknown_entries,
                "current_count": len(current_entries_from_file(relpath)),
                "word_issues": ["manual_review_reported"] + (["has_unknown_entries"] if unknown_entries else []),
            }

    items = [all_words[word] for word in sorted(all_words)]
    OUT.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"items={len(items)}")
    print(f"manifest={OUT}")


if __name__ == "__main__":
    main()
