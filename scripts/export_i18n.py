#!/usr/bin/env python3
"""Generate the CraftLife i18n catalogue from translations.py.

translations.py stays the single source of truth (UPDATE_RULES.md P2). This
script emits it to the two places that actually consume it:

  1. packages/craftlife-core/src/i18n/messages.json
     The canonical, TypeScript-consumable catalogue. This is the copy the
     future Android client imports, so it lives in the shared package.

  2. web/public/i18n/messages.json
     A static asset the desktop shell serves over HTTP; web/src/i18n.ts
     fetches it as the offline fallback before /api/i18n overlays it.

Both are generated, identical, and must never be edited by hand. Emitting both
here replaces the old manual "export then copy" step.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from translations import TRANSLATIONS  # noqa: E402

TARGETS = (
    os.path.join(ROOT, "packages", "craftlife-core", "src", "i18n", "messages.json"),
    os.path.join(ROOT, "web", "public", "i18n", "messages.json"),
)


def main():
    id_map, en_map = {}, {}
    for key, pair in TRANSLATIONS.items():
        if not isinstance(pair, (tuple, list)) or len(pair) < 2:
            continue
        id_map[key] = pair[0]
        en_map[key] = pair[1]

    for out in TARGETS:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"id": id_map, "en": en_map}, f, ensure_ascii=False)
        print(f"wrote {out} keys={len(id_map)}")


if __name__ == "__main__":
    main()
