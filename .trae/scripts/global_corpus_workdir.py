#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path


WORK_DIR = Path(os.environ.get("GLOBAL_CORPUS_WORK_DIR", "/data/user/work"))
WORK_DIR.mkdir(parents=True, exist_ok=True)


def work_path(*parts: str) -> Path:
    return WORK_DIR.joinpath(*parts)
