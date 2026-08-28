#!/usr/bin/env python3
"""Generate web/src/i18n/messages.json from translations.py."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from translations import TRANSLATIONS  # noqa: E402

OUT = os.path.join(ROOT, "web", "src", "i18n", "messages.json")


def main():
    id_map, en_map = {}, {}
    for key, pair in TRANSLATIONS.items():
        if not isinstance(pair, (tuple, list)) or len(pair) < 2:
            continue
        id_map[key] = pair[0]
        en_map[key] = pair[1]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"id": id_map, "en": en_map}, f, ensure_ascii=False)
    print(f"wrote {OUT} keys={len(id_map)}")


if __name__ == "__main__":
    main()
