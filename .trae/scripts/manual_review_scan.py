#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨批次扫描人工复核 / Unknown / 伪例句问题，输出统一 repair manifest。

输出：
- /data/user/work/manual_review_manifest.json
- /data/user/work/manual_review_manifest.tsv
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from manual_review_registry import REPO, get_scopes
OUT_JSON = Path("/data/user/work/manual_review_manifest.json")
OUT_TSV = Path("/data/user/work/manual_review_manifest.tsv")

TAG_RE = re.compile(r"`\[([^\]]+)\]`\s*$")
PLACEHOLDER_RE = re.compile(
    r"(please provide an example sentence using the word\b|i learned the word\b)",
    flags=re.I,
)
AUXILIARIES = {
    "am", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did",
    "have", "has", "had",
    "can", "could", "may", "might", "must", "shall", "should", "will", "would",
}


@dataclass
class EvidenceRow:
    word: str
    sentence: str
    tag: str
    source: str
    url: str


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as f:
        return f.read()


def extract_word_freq(text: str) -> str:
    m = re.search(r"^word_freq:\s*(.+?)\s*$", text, flags=re.M)
    return (m.group(1).strip() if m else "").strip('"').strip("'")


def required_corpus_count(word_freq: str) -> int:
    return 2 if word_freq == "超纲词" else 3


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
    alts = [re.escape(x) for x in dict.fromkeys(forms)]
    pat = re.compile(rf"\b(?:{'|'.join(alts)})\b", flags=re.I)
    return bool(pat.search(s))


def normalize_sentence(s: str) -> str:
    s = re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()
    s = s.strip('"\'“”‘’')
    s = s.rstrip('"\'“”‘’').strip()
    if not s:
        return ""
    if s[0].islower():
        s = s[0].upper() + s[1:]
    if s and s[-1] not in ".?!":
        s += "."
    return s


def norm_key(s: str) -> str:
    s = normalize_sentence(s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


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


def parse_report(report_path: Path) -> Tuple[Dict[Tuple[str, str], EvidenceRow], Dict[str, List[str]]]:
    if not report_path.exists():
        return {}, {}
    text = read_text(report_path)
    evidence: Dict[Tuple[str, str], EvidenceRow] = {}
    anomalies: Dict[str, List[str]] = {}

    in_anomaly = False
    in_table = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "## 异常/人工复核":
            in_anomaly = True
            in_table = False
            continue
        if line.startswith("## ") and line != "## 异常/人工复核":
            in_anomaly = False
        if line.startswith("| word | sentence | tag | source | url |"):
            in_table = True
            in_anomaly = False
            continue
        if in_anomaly and line.startswith("- "):
            body = line[2:].strip()
            word = body.split(":", 1)[0].strip()
            anomalies.setdefault(word, []).append(body)
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            if line.startswith("|---|"):
                continue
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) != 5:
                continue
            word, sentence, tag, source, url = parts
            sent = normalize_sentence(sentence)
            if not word or not sent:
                continue
            evidence[(word, norm_key(sent))] = EvidenceRow(
                word=word,
                sentence=sent,
                tag=tag,
                source=source or "Unknown",
                url=url,
            )
    return evidence, anomalies


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


def parse_corpus_entries(text: str) -> List[Dict[str, str]]:
    block = corpus_block(text)
    out: List[Dict[str, str]] = []
    if not block:
        return out
    for ln in block.splitlines():
        m = re.match(r"^>\s*-\s+(.*)$", ln)
        if not m:
            continue
        raw = m.group(1).rstrip()
        tag_m = TAG_RE.search(raw)
        tag = tag_m.group(1) if tag_m else ""
        sent = TAG_RE.sub("", raw).rstrip() if tag_m else raw
        out.append(
            {
                "raw": raw,
                "sentence": normalize_sentence(sent),
                "tag": f"[{tag}]" if tag else "",
            }
        )
    return out


def main() -> None:
    group = sys.argv[1] if len(sys.argv) > 1 else "all"
    scopes = get_scopes(group)
    manifest: List[Dict[str, object]] = []
    total_entries = 0
    total_problem_words = 0

    for scope in scopes:
        list_file = Path(scope["list_path"])
        report_file = Path(scope["report_path"])
        evidence_map, anomaly_map = parse_report(report_file)
        relpaths = [ln.strip() for ln in read_text(list_file).splitlines() if ln.strip()]

        for relpath in relpaths:
            path = REPO / relpath
            word = Path(relpath).stem
            text = read_text(path)
            word_freq = extract_word_freq(text)
            required = required_corpus_count(word_freq)
            corpus_entries = parse_corpus_entries(text)
            total_entries += len(corpus_entries)

            item_entries: List[Dict[str, object]] = []
            word_issues: List[str] = []
            valid_entry_count = 0

            if not corpus_entries:
                word_issues.append("missing_corpus_block")

            for entry in corpus_entries:
                sent = str(entry["sentence"])
                issues: List[str] = []
                evidence = evidence_map.get((word, norm_key(sent)))
                source = evidence.source if evidence else "Unknown"
                url = evidence.url if evidence else ""

                if PLACEHOLDER_RE.search(sent):
                    issues.append("pseudo_placeholder")
                if re.search(r"[\u4e00-\u9fff]", sent):
                    issues.append("contains_chinese")
                if not keep_if_contains_word(word, sent):
                    issues.append("missing_target_word")
                if not looks_like_full_sentence(sent):
                    issues.append("pseudo_fragment")
                if source == "Unknown":
                    issues.append("unknown_source")
                if word in anomaly_map:
                    issues.append("manual_review_reported")
                if not entry["tag"]:
                    issues.append("missing_tag")

                if not {"pseudo_placeholder", "contains_chinese", "missing_target_word", "pseudo_fragment"} & set(issues):
                    valid_entry_count += 1

                item_entries.append(
                    {
                        "raw": entry["raw"],
                        "sentence": sent,
                        "norm_key": norm_key(sent),
                        "tag": entry["tag"],
                        "source": source,
                        "url": url,
                        "issues": sorted(set(issues)),
                    }
                )

            missing_count = max(0, required - valid_entry_count)
            if missing_count > 0:
                word_issues.append("count_insufficient")
            if word in anomaly_map:
                word_issues.append("manual_review_reported")
            if any("unknown_source" in x["issues"] for x in item_entries):
                word_issues.append("has_unknown_source")
            if any("pseudo_placeholder" in x["issues"] for x in item_entries):
                word_issues.append("has_placeholder")
            if any("pseudo_fragment" in x["issues"] for x in item_entries):
                word_issues.append("has_fragment")

            if word_issues or any(x["issues"] for x in item_entries):
                total_problem_words += 1

            manifest.append(
                {
                    "scope_id": scope["scope_id"],
                    "batch_id": scope["display_batch_id"],
                    "group": scope["group"],
                    "directory": scope["directory"],
                    "report_path": str(report_file),
                    "list_path": str(list_file),
                    "relpath": relpath,
                    "word": word,
                    "word_freq": word_freq,
                    "required_count": required,
                    "current_count": len(corpus_entries),
                    "valid_entry_count": valid_entry_count,
                    "missing_count": missing_count,
                    "word_issues": sorted(set(word_issues)),
                    "anomalies": anomaly_map.get(word, []),
                    "entries": item_entries,
                }
            )

    OUT_JSON.write_text(
        json.dumps(
            {
                "groups": sorted({str(scope["group"]) for scope in scopes}),
                "scope_ids": [str(scope["scope_id"]) for scope in scopes],
                "total_words": len(manifest),
                "total_entries": total_entries,
                "problem_words": total_problem_words,
                "items": manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "\t".join(
            [
                "batch_id",
                "relpath",
                "word",
                "word_freq",
                "required_count",
                "current_count",
                "valid_entry_count",
                "missing_count",
                "word_issues",
                "entry_issue_count",
            ]
        )
    ]
    for item in manifest:
        entry_issue_count = sum(1 for e in item["entries"] if e["issues"])
        lines.append(
            "\t".join(
                [
                    str(item["batch_id"]),
                    str(item["relpath"]),
                    str(item["word"]),
                    str(item["word_freq"]),
                    str(item["required_count"]),
                    str(item["current_count"]),
                    str(item["valid_entry_count"]),
                    str(item["missing_count"]),
                    ",".join(item["word_issues"]),
                    str(entry_issue_count),
                ]
            )
        )
    OUT_TSV.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"total_words={len(manifest)}")
    print(f"problem_words={total_problem_words}")
    print(f"json={OUT_JSON}")
    print(f"tsv={OUT_TSV}")


if __name__ == "__main__":
    main()
