#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整理 browser fallback 队列与人工补录命中结果。

用途：
- 读取 `/data/user/work/manual_review_browser_queue.json`
- 如果存在 `/data/user/work/manual_review_browser_hits_raw.json`，则做规范化输出
- 输出 `/data/user/work/manual_review_browser_hits.json`

说明：
- 本脚本不直接驱动浏览器；浏览器交互由外部 browser 工具完成。
- 本脚本的职责是把 browser 命中的句子规范化，供 apply / report 脚本消费。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List


QUEUE = Path("/data/user/work/manual_review_browser_queue.json")
RAW_HITS = Path("/data/user/work/manual_review_browser_hits_raw.json")
OUT_HITS = Path("/data/user/work/manual_review_browser_hits.json")


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


def main() -> None:
    queue_obj = {"items": []}
    if QUEUE.exists():
        queue_obj = json.loads(QUEUE.read_text(encoding="utf-8"))

    raw_obj = {"items": []}
    if RAW_HITS.exists():
        raw_obj = json.loads(RAW_HITS.read_text(encoding="utf-8"))

    queue_words = {(item.get("scope_id", ""), item.get("word", "")): item for item in queue_obj.get("items", [])}
    normalized_hits: List[Dict[str, object]] = []
    seen = set()

    for item in raw_obj.get("items", []):
        scope_id = item.get("scope_id", "").strip()
        word = item.get("word", "").strip()
        sentence = normalize_sentence(item.get("sentence", ""))
        if not word or not sentence:
            continue
        key = (scope_id, word, norm_key(sentence))
        if key in seen:
            continue
        seen.add(key)
        q_item = queue_words.get((scope_id, word), {})
        normalized_hits.append(
            {
                "scope_id": scope_id or q_item.get("scope_id", ""),
                "word": word,
                "relpath": item.get("relpath", q_item.get("relpath", "")),
                "sentence": sentence,
                "tag": item.get("tag", "[例]"),
                "source": item.get("source", "Browser"),
                "url": item.get("url", ""),
                "acquisition_mode": "browser",
            }
        )

    OUT_HITS.write_text(
        json.dumps(
            {
                "queue_count": len(queue_obj.get("items", [])),
                "hit_count": len(normalized_hits),
                "items": normalized_hits,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"queue_count={len(queue_obj.get('items', []))}")
    print(f"hit_count={len(normalized_hits)}")
    print(f"out={OUT_HITS}")


if __name__ == "__main__":
    main()
