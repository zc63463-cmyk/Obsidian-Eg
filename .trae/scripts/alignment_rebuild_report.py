#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建本轮 GitHub 拉取内容格式对齐与语料修复报告。
"""

from __future__ import annotations

import json
from pathlib import Path


REPO = Path("/workspace/Obsidian-Eg")
WORK = Path("/data/user/work")
OUT_MD = REPO / ".trae" / "reports" / "GitHub拉取内容格式对齐与语料修复报告.md"


def load_json(name: str):
    return json.loads((WORK / name).read_text(encoding="utf-8"))


def main() -> None:
    scope = load_json("alignment_scope.json")
    scan_summary = load_json("alignment_manifest_summary.json")
    structure = load_json("alignment_structure_stats.json")
    corpus = load_json("alignment_apply_corpus_stats.json")
    validate = load_json("alignment_validate_report.json")

    lines = [
        "# GitHub 拉取内容格式对齐与语料修复报告",
        "",
        "## 范围",
        "",
        f"- scope 文件数：{len(scope['items'])}",
        f"- 全量词汇词条：{len(scope.get('all_vocab_paths', []))}",
        "",
        "## 初始扫描",
        "",
        f"- 扫描文件数：{scan_summary['files_scanned']}",
        f"- 初始存在问题文件数：{scan_summary['files_with_problems']}",
        "",
        "### 问题分布",
        "",
    ]
    for key, value in scan_summary["problem_counts"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## 修复执行",
            "",
            f"- 结构归一触达文件数：{structure['touched_files']}",
            f"- 语料修复触达文件数：{corpus['files_changed']}",
            f"- 自动重写条目数：{corpus['rewritten']}",
            f"- 自动补足条目数：{corpus['top_up_added']}",
            f"- 去重条目数：{corpus['deduped']}",
            "",
            "## 最终验收",
            "",
            f"- bad_count: {validate['bad_count']}",
        ]
    )

    if validate["bad_files"]:
        lines.extend(["", "### 未通过文件", ""])
        for item in validate["bad_files"]:
            lines.append(f"- {item['relpath']}")
            for err in item["errors"]:
                lines.append(f"  - {err}")
    else:
        lines.extend(
            [
                "- 本轮 scope 在统一验收下全部通过",
                "- 无需触发额外人工复核队列",
            ]
        )

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report={OUT_MD}")


if __name__ == "__main__":
    main()
