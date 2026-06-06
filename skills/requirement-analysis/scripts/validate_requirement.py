#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate requirement-analysis handoff JSON.

This validator is intentionally lightweight. It verifies that the machine
handoff is structurally usable by later workflow stages and separates draft
state from final state without inventing business facts.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


PENDING_MARKERS = ("待确认", "[待确认]", "TBD", "TODO", "UNDECIDED")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def contains_marker(value: Any) -> bool:
    if isinstance(value, str):
        return any(marker in value for marker in PENDING_MARKERS)
    if isinstance(value, dict):
        return any(contains_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_marker(item) for item in value)
    return False


def validate(data: Any, handoff_path: Path, project_root: str = "") -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "success": False,
            "errors": ["handoff JSON must be an object"],
            "warnings": [],
        }

    if is_blank(data.get("schema_version")):
        errors.append("schema_version is required")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source object is required")
        source = {}

    status = str(source.get("requirement_status") or "").strip()
    if status not in {"final", "draft"}:
        errors.append("source.requirement_status must be final or draft")

    product = data.get("product")
    if not isinstance(product, dict):
        errors.append("product object is required")
        product = {}
    if is_blank(product.get("product_id")):
        errors.append("product.product_id is required")
    if is_blank(product.get("product_version")):
        errors.append("product.product_version is required")

    requirement_items = as_list(data.get("requirement_items"))
    if not requirement_items:
        errors.append("requirement_items must contain at least one item")
    for index, item in enumerate(requirement_items, start=1):
        if not isinstance(item, dict):
            errors.append(f"requirement_items[{index}] must be an object")
            continue
        item_id = item.get("id") or f"#{index}"
        if is_blank(item.get("id")):
            errors.append(f"requirement_items[{index}].id is required")
        if is_blank(item.get("title")) and is_blank(item.get("summary")):
            errors.append(f"requirement_items[{item_id}] needs title or summary")
        criteria = as_list(item.get("acceptance_criteria"))
        if not criteria:
            message = f"requirement_items[{item_id}].acceptance_criteria is empty"
            if status == "final":
                errors.append(message)
            else:
                warnings.append(message)
        if contains_marker(item) and status == "final":
            errors.append(f"requirement_items[{item_id}] contains pending markers")

    platform_tasks = data.get("platform_dependency_tasks")
    if not isinstance(platform_tasks, list):
        errors.append("platform_dependency_tasks must be a list")
    elif not platform_tasks:
        warnings.append("platform_dependency_tasks is empty; confirm design-phase does not need platform dependency search")
    else:
        for index, task in enumerate(platform_tasks, start=1):
            if not isinstance(task, dict):
                errors.append(f"platform_dependency_tasks[{index}] must be an object")
                continue
            task_id = task.get("task_id") or f"#{index}"
            if is_blank(task.get("from_requirement")):
                errors.append(f"platform_dependency_tasks[{task_id}].from_requirement is required")
            if is_blank(task.get("design_search_intent")):
                warnings.append(f"platform_dependency_tasks[{task_id}].design_search_intent is empty")

    target_resolution = data.get("target_object_resolution")
    if target_resolution is not None and not isinstance(target_resolution, list):
        errors.append("target_object_resolution must be a list when present")
    for index, resolution in enumerate(as_list(target_resolution), start=1):
        if not isinstance(resolution, dict):
            errors.append(f"target_object_resolution[{index}] must be an object")
            continue
        if str(resolution.get("status") or "").strip() == "open":
            message = f"target_object_resolution[{index}].status is open"
            if status == "final":
                errors.append(message)
            else:
                warnings.append(message)

    open_questions = as_list(data.get("open_questions"))
    if status == "final" and open_questions:
        errors.append("final requirement handoff must not contain open_questions")
    if status == "draft" and not open_questions and contains_marker(data):
        warnings.append("draft contains pending markers but open_questions is empty")

    if status == "final" and contains_marker(data):
        errors.append("final requirement handoff contains pending markers")

    return {
        "success": not errors,
        "checked_at": now_iso(),
        "validator": "requirement-analysis/scripts/validate_requirement.py",
        "handoff": str(handoff_path),
        "project_root": project_root,
        "requirement_status": status or "",
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Validate requirement-analysis handoff JSON.")
    parser.add_argument("--handoff", required=True, help="Path to requirement-handoff.json")
    parser.add_argument("--output", required=True, help="Path to requirement-validation.json")
    parser.add_argument("--project-root", default="", help="Project root path for traceability")
    args = parser.parse_args()

    handoff_path = Path(args.handoff).resolve()
    output_path = Path(args.output).resolve()
    if not handoff_path.exists():
        result = {
            "success": False,
            "checked_at": now_iso(),
            "validator": "requirement-analysis/scripts/validate_requirement.py",
            "handoff": str(handoff_path),
            "project_root": args.project_root,
            "requirement_status": "",
            "errors": ["handoff file does not exist"],
            "warnings": [],
        }
        write_json(output_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        data = read_json(handoff_path)
        result = validate(data, handoff_path, args.project_root)
    except json.JSONDecodeError as exc:
        result = {
            "success": False,
            "checked_at": now_iso(),
            "validator": "requirement-analysis/scripts/validate_requirement.py",
            "handoff": str(handoff_path),
            "project_root": args.project_root,
            "requirement_status": "",
            "errors": [f"invalid JSON: {exc}"],
            "warnings": [],
        }

    write_json(output_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
