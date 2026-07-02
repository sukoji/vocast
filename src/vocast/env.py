from __future__ import annotations

import os
from pathlib import Path

from vocast.paths import ROOT


def load_env() -> None:
    for p in (
        ROOT / ".env",
        ROOT.parent / "dialect" / "llm_dialect_test" / ".env",
    ):
        if not p.is_file():
            continue
        for ln in p.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
