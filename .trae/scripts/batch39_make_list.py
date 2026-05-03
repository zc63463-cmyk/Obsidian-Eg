#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成第39批（L0_超纲词 第9批：801–900）清单：
- 目录：Wiki/L0_超纲词
- 排序：Python sorted(按文件名)
- 切片：files[800:900]
输出：
- /data/user/work/batch39_files.txt（运行时清单）
- .trae/batches/batch39_files.txt（清单落库，范围基准）
"""

from pathlib import Path


REPO = Path("/workspace/Obsidian-Eg")
DIR = REPO / "Wiki" / "L0_超纲词"
OUT_WORK = Path("/data/user/work/batch39_files.txt")
OUT_REPO = REPO / ".trae" / "batches" / "batch39_files.txt"


def main() -> None:
    files = sorted([p for p in DIR.glob("*.md") if p.is_file()], key=lambda p: p.name)
    batch = files[800:900]
    if len(batch) != 100:
        raise SystemExit(f"Expected 100 files, got {len(batch)} (total={len(files)})")
    if batch[0].name != "revitalize.md" or batch[-1].name != "stylist.md":
        raise SystemExit(
            f"Unexpected boundaries: first={batch[0].name} last={batch[-1].name}"
        )

    rels = [str(p.relative_to(REPO)).replace("\\", "/") for p in batch]
    OUT_WORK.write_text("\n".join(rels) + "\n", encoding="utf-8")
    OUT_REPO.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPO.write_text("\n".join(rels) + "\n", encoding="utf-8")

    print(f"Wrote {len(rels)} files -> {OUT_WORK}")
    print(f"Wrote {len(rels)} files -> {OUT_REPO}")
    print(f"First: {rels[0]}")
    print(f"Last:  {rels[-1]}")


if __name__ == "__main__":
    main()
