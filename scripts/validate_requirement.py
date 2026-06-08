#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate artifacts/01_requirement.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate requirement artifact.")
    parser.add_argument("--input", default="artifacts/01_requirement.json")
    args = parser.parse_args()

    path = Path(args.input)
    errors: list[str] = []
    if not path.exists():
        errors.append(f"file not found: {path}")
        data = {}
    else:
        data = json.loads(path.read_text(encoding="utf-8-sig"))

    for key in ["project_name", "business_goal", "functional_requirements", "acceptance_criteria"]:
        if not data.get(key):
            errors.append(f"{key} is required")

    product = data.get("product") if isinstance(data.get("product"), dict) else {}
    if not product.get("product_id"):
        errors.append("product.product_id is required")
    if not product.get("product_version"):
        errors.append("product.product_version is required")

    if data.get("status") == "final" and data.get("open_questions"):
        errors.append("final requirement must not contain open_questions")

    result = {"success": not errors, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
