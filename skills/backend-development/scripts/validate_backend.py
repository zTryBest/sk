#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate backend-development handoff JSON."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


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


def json_error_detail(path: Path, exc: json.JSONDecodeError, radius: int = 1) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "error_type": "invalid_json",
        "message": exc.msg,
        "line": exc.lineno,
        "column": exc.colno,
        "position": exc.pos,
        "repair_action": "rewrite_with_json_serializer",
    }
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError as read_exc:
        detail["context_error"] = str(read_exc)
        return detail
    start = max(1, exc.lineno - radius)
    end = min(len(lines), exc.lineno + radius)
    detail["context"] = [{"line": line_no, "text": lines[line_no - 1][:240]} for line_no in range(start, end + 1)]
    return detail


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate(data: Any, handoff_path: Path, project_root: str = "") -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "success": False,
            "checked_at": now_iso(),
            "validator": "backend-development/scripts/validate_backend.py",
            "handoff": str(handoff_path),
            "project_root": project_root,
            "errors": ["handoff JSON must be an object"],
            "warnings": [],
        }

    if is_blank(data.get("schema_version")):
        errors.append("schema_version is required")

    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    status = str(source.get("backend_status") or "").strip()
    if status != "completed":
        errors.append("source.backend_status must be completed")

    scaffold = data.get("scaffold") if isinstance(data.get("scaffold"), dict) else {}
    source_dir_text = str(scaffold.get("source_dir") or "").strip()
    if not source_dir_text:
        errors.append("scaffold.source_dir is required")
        source_dir = None
    else:
        source_dir = Path(source_dir_text)
        if not source_dir.exists():
            errors.append(f"scaffold.source_dir does not exist: {source_dir}")
        elif not source_dir.is_dir():
            errors.append(f"scaffold.source_dir is not a directory: {source_dir}")

    manifest_text = str(scaffold.get("manifest") or scaffold.get("manifest_path") or "").strip()
    if manifest_text:
        manifest_path = Path(manifest_text)
        if not manifest_path.is_absolute() and source_dir is not None:
            manifest_path = source_dir / manifest_path
        if not manifest_path.exists():
            errors.append(f"scaffold manifest does not exist: {manifest_path}")
        elif not manifest_path.is_file():
            errors.append(f"scaffold manifest is not a file: {manifest_path}")

    endpoint = str(scaffold.get("endpoint") or scaffold.get("service_url") or "").strip()
    if endpoint and not endpoint.endswith("/v1/frame/frame"):
        warnings.append("scaffold endpoint should end with /v1/frame/frame")

    changed_files = as_list(data.get("changed_files"))
    if not changed_files:
        errors.append("changed_files must contain at least one file")
    for item in changed_files:
        path_text = str(item or "").strip()
        if not path_text:
            errors.append("changed_files contains blank path")
            continue
        path = Path(path_text)
        if not path.is_absolute() and source_dir is not None:
            path = source_dir / path
        if not path.exists():
            errors.append(f"changed file does not exist: {path}")

    build = data.get("build_and_test") if isinstance(data.get("build_and_test"), dict) else {}
    commands = as_list(build.get("commands_run"))
    if not commands:
        errors.append("build_and_test.commands_run must contain at least one command")
    if build.get("compile_success") is not True:
        errors.append("build_and_test.compile_success must be true")
    if build.get("tests_success") is not True:
        warnings.append("build_and_test.tests_success is not true")

    if as_list(data.get("open_issues")):
        warnings.append("open_issues is not empty")

    return {
        "success": not errors,
        "checked_at": now_iso(),
        "validator": "backend-development/scripts/validate_backend.py",
        "handoff": str(handoff_path),
        "project_root": project_root,
        "backend_status": status,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Validate backend-development handoff JSON.")
    parser.add_argument("--handoff", required=True, help="Path to backend-code-result.json")
    parser.add_argument("--output", required=True, help="Path to backend-validation.json")
    parser.add_argument("--project-root", default="", help="Project root path for traceability")
    args = parser.parse_args()

    handoff_path = Path(args.handoff).resolve()
    output_path = Path(args.output).resolve()
    if not handoff_path.exists():
        result = {
            "success": False,
            "checked_at": now_iso(),
            "validator": "backend-development/scripts/validate_backend.py",
            "handoff": str(handoff_path),
            "project_root": args.project_root,
            "backend_status": "",
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
            "validator": "backend-development/scripts/validate_backend.py",
            "handoff": str(handoff_path),
            "project_root": args.project_root,
            "backend_status": "",
            "errors": [f"invalid JSON: {exc}; rewrite the file with a JSON serializer such as json.dump(..., ensure_ascii=False)"],
            "json_error": json_error_detail(handoff_path, exc),
            "warnings": [],
        }

    write_json(output_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
