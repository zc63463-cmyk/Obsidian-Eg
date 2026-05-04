#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path


WORK = Path("/data/user/work")
OUT_MD = Path("/workspace/Obsidian-Eg/.trae/reports/P2_template_corpus_修复报告.md")


def load_json(name: str):
    return json.loads((WORK / name).read_text(encoding="utf-8"))


def main() -> None:
    scope = load_json("p2_template_corpus_scope.json")
    apply_stats = load_json("p2_template_apply_stats.json")
    validate = load_json("p2_template_validate_report.json")
    queue = load_json("p2_template_browser_queue.json")
    lines = [
        "# P2 template_corpus 修复报告",
        "",
        f"- scope 文件数：{len(scope['items'])}",
        f"- 静态写回文件数：{apply_stats['changed_file_count']}",
        f"- unresolved 文件数：{apply_stats['unresolved_file_count']}",
        f"- 浏览器队列数：{len(queue['items'])}",
        f"- 当前 bad_count：{validate['bad_count']}",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report={OUT_MD}")


if __name__ == "__main__":
    main()
