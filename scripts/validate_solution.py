#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate artifacts/02_solution.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate solution artifact.")
    parser.add_argument("--input", default="artifacts/02_solution.json")
    args = parser.parse_args()

    path = Path(args.input)
    errors: list[str] = []
    if not path.exists():
        errors.append(f"file not found: {path}")
        data = {}
    else:
        data = json.loads(path.read_text(encoding="utf-8-sig"))

    for key in ["architecture", "implementation_classification", "modules", "api_design"]:
        if not data.get(key):
            errors.append(f"{key} is required")

    classifications = data.get("implementation_classification")
    if isinstance(classifications, list):
        needs_mcp = [item for item in classifications if isinstance(item, dict) and item.get("mode") in {"BASELINE_API_REUSE", "HYBRID"}]
        if needs_mcp and not data.get("mcp_call_log"):
            errors.append("mcp_call_log is required when baseline API reuse is used")
        if needs_mcp and not data.get("selected_baseline_apis"):
            errors.append("selected_baseline_apis is required when baseline API reuse is used")

    if data.get("status") == "final" and data.get("open_decisions"):
        errors.append("final solution must not contain open_decisions")

    result = {"success": not errors, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
