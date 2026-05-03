#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from manual_review_registry import REPO, get_scopes


def main() -> None:
    count = 0
    for scope in get_scopes("early"):
        dir_path = REPO / str(scope["directory"])
        files = sorted([p for p in dir_path.glob("*.md") if p.is_file()], key=lambda p: p.name)
        batch = files[int(scope["slice_start"]):int(scope["slice_end"])]
        rels = [str(p.relative_to(REPO)).replace("\\", "/") for p in batch]
        list_path = Path(scope["list_path"])
        list_path.parent.mkdir(parents=True, exist_ok=True)
        list_path.write_text("\n".join(rels) + "\n", encoding="utf-8")
        print(f"{scope['scope_id']}\t{len(rels)}\t{list_path.name}")
        count += 1
    print(f"generated={count}")


if __name__ == "__main__":
    main()
