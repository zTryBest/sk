#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate artifacts/04_plan.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate plan artifact.")
    parser.add_argument("--input", default="artifacts/04_plan.json")
    args = parser.parse_args()

    path = Path(args.input)
    errors: list[str] = []
    if not path.exists():
        errors.append(f"file not found: {path}")
        data = {}
    else:
        data = json.loads(path.read_text(encoding="utf-8-sig"))

    for key in ["backend_tasks", "frontend_tasks", "test_tasks", "api_contracts", "execution_order"]:
        if not data.get(key):
            errors.append(f"{key} is required")

    if data.get("status") == "final" and data.get("open_decisions"):
        errors.append("final plan must not contain open_decisions")

    result = {"success": not errors, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
