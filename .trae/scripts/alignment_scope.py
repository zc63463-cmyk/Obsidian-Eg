#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成本轮格式对齐与语料修复范围：
- git 变更中的 Wiki 词条
- 指定 batch 文件中的词条
- 指定报告中提到的 Wiki 词条

输出：
- /data/user/work/alignment_scope.json
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


REPO = Path("/workspace/Obsidian-Eg")
OUT_JSON = Path("/data/user/work/alignment_scope.json")
VOCAB_DIRS = ["L0_单词集合", "L0_基础词", "L0_超纲词"]
WIKI_RELPATH_RE = re.compile(r"Wiki/[^\s`'\"]+?\.md")


def parse_git_changed_paths(raw: str) -> List[str]:
    paths = set()
    for line in raw.splitlines():
        path = line.strip().strip('"')
        if not path.startswith("Wiki/"):
            continue
        if not path.endswith(".md"):
            continue
        paths.add(path)
    return sorted(paths)


def parse_batch_relpaths(text: str) -> List[str]:
    paths = set()
    for line in text.splitlines():
        path = line.strip().strip('"')
        if path.startswith("Wiki/") and path.endswith(".md"):
            paths.add(path)
    return sorted(paths)


def parse_report_relpaths(text: str) -> List[str]:
    return sorted(set(WIKI_RELPATH_RE.findall(text)))


def collect_all_vocab_relpaths(candidates: Iterable[str] | None = None) -> List[str]:
    if candidates is None:
        found = []
        for dirname in VOCAB_DIRS:
            root = REPO / "Wiki" / dirname
            if not root.exists():
                continue
            found.extend(
                str(p.relative_to(REPO)).replace("\\", "/")
                for p in sorted(root.glob("*.md"))
            )
        candidates = found

    allowed_prefixes = tuple(f"Wiki/{name}/" for name in VOCAB_DIRS)
    out = set()
    for rel in candidates:
        if rel.startswith(allowed_prefixes) and rel.endswith(".md"):
            out.add(rel)
    return sorted(out)


def extract_word_freq(text: str) -> str:
    m = re.search(r"^word_freq:\s*(.+?)\s*$", text, flags=re.M)
    return (m.group(1).strip() if m else "").strip('"').strip("'")


def load_word_freq_map(paths: Iterable[str]) -> Dict[str, str]:
    freq_map: Dict[str, str] = {}
    for rel in paths:
        p = REPO / rel
        if not p.exists():
            continue
        freq_map[rel] = extract_word_freq(p.read_text(encoding="utf-8"))
    return freq_map


def build_scope_items(
    git_paths: Sequence[str],
    batch_paths: Sequence[str],
    report_paths: Sequence[str],
    freq_map: Dict[str, str],
) -> List[Dict[str, object]]:
    sources: Dict[str, set[str]] = {}
    for label, paths in (
        ("git", git_paths),
        ("batch", batch_paths),
        ("report", report_paths),
    ):
        for rel in paths:
            sources.setdefault(rel, set()).add(label)

    items: List[Dict[str, object]] = []
    for rel in sorted(sources):
        items.append(
            {
                "relpath": rel,
                "word": Path(rel).stem,
                "word_freq": freq_map.get(rel, ""),
                "source_scope": sorted(sources[rel]),
                "problem_flags": [],
            }
        )
    return items


def git_changed_paths(base_ref: str = "origin/main") -> List[str]:
    cp = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}..HEAD"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_git_changed_paths(cp.stdout)


def read_existing_paths(files: Sequence[Path], parser) -> List[str]:
    out = set()
    for p in files:
        if not p.exists():
            continue
        out.update(parser(p.read_text(encoding="utf-8")))
    return sorted(out)


def main() -> None:
    all_vocab_paths = collect_all_vocab_relpaths()
    freq_map = load_word_freq_map(all_vocab_paths)
    items = [
        {
            "relpath": rel,
            "word": Path(rel).stem,
            "word_freq": freq_map.get(rel, ""),
            "source_scope": ["all_vocab"],
            "problem_flags": [],
        }
        for rel in all_vocab_paths
    ]
    payload = {
        "all_vocab_paths": all_vocab_paths,
        "items": items,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"scope_items={len(items)}")
    print(f"out={OUT_JSON}")


if __name__ == "__main__":
    main()
