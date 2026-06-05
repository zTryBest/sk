#!/usr/bin/env python3
"""Validate requirement-analysis handoff artifacts.

This validator is intentionally conservative. It checks the machine-readable
handoff contract that design-phase should consume, plus a few high-signal
properties of the generated Markdown document.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any


TARGET_ACTION_KEYWORDS = (
    "通知",
    "推送",
    "发送",
    "分派",
    "审批",
    "抄送",
    "派单",
    "升级",
    "授权",
    "订阅",
    "触达",
    "负责人",
    "接收方",
    "接收人",
    "联系人",
    "处理人",
    "审核人",
    "参与人",
    "notify",
    "notification",
    "push",
    "send",
    "dispatch",
    "assign",
    "approve",
    "recipient",
    "receiver",
    "contact",
)

FINAL_STATUS_VALUES = {"final", "最终版", "正式版"}
PENDING_MARKERS = ("[待确认]", "待确认")


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        errors.append(f"handoff file not found: {path}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"handoff is not valid JSON: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append("handoff root must be a JSON object")
        return {}
    return data


def _resolve_path(value: str | None, base_dir: Path) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text_blob(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return " ".join(_text_blob(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_text_blob(item) for item in value.values())
    return str(value)


def _is_final_status(status: Any) -> bool:
    return str(status or "").strip().lower() in FINAL_STATUS_VALUES


def _contains_target_action(item: dict[str, Any]) -> bool:
    blob = _text_blob(
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "summary": item.get("summary"),
            "description": item.get("description"),
            "business_rules": item.get("business_rules"),
            "data_rules": item.get("data_rules"),
            "acceptance_criteria": item.get("acceptance_criteria"),
            "platform_dependency_summary": item.get("platform_dependency_summary"),
        }
    ).lower()
    return any(keyword.lower() in blob for keyword in TARGET_ACTION_KEYWORDS)


def _has_open_target_risk(item_id: str, data: dict[str, Any]) -> bool:
    blob = _text_blob(
        {
            "open_questions": data.get("open_questions"),
            "open_risks_for_design": data.get("open_risks_for_design"),
            "platform_dependency_tasks": data.get("platform_dependency_tasks"),
        }
    ).lower()
    return item_id.lower() in blob and any(
        keyword.lower() in blob for keyword in TARGET_ACTION_KEYWORDS
    )


def _inside_project(path: Path, project_root: Path) -> bool:
    try:
        path.resolve().relative_to(project_root.resolve())
        return True
    except ValueError:
        return False


def validate(handoff_path: Path, project_root: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    handoff_path = handoff_path.resolve()
    base_dir = handoff_path.parent
    project_root = (project_root or Path.cwd()).resolve()

    data = _load_json(handoff_path, errors)
    if not data:
        return {
            "success": False,
            "errors": errors,
            "warnings": warnings,
            "checked_at": _now_iso(),
            "input": str(handoff_path),
        }

    if not _inside_project(handoff_path, project_root):
        errors.append(
            f"handoff must be under the project root: handoff={handoff_path}, project_root={project_root}"
        )

    source = data.get("source") or {}
    product = data.get("product") or {}
    requirement_items = data.get("requirement_items")
    platform_tasks = data.get("platform_dependency_tasks")
    target_resolution = data.get("target_object_resolution")
    open_questions = _as_list(data.get("open_questions"))
    open_risks = _as_list(data.get("open_risks_for_design"))

    requirement_doc_path = _resolve_path(source.get("requirement_doc"), base_dir)
    requirement_status = source.get("requirement_status")
    is_final = _is_final_status(requirement_status)

    for field_name, value in (
        ("source.requirement_doc", source.get("requirement_doc")),
        ("source.requirement_status", requirement_status),
        ("product.product_id", product.get("product_id")),
        ("product.product_version", product.get("product_version")),
    ):
        if not value:
            errors.append(f"missing required field: {field_name}")

    if requirement_doc_path is None:
        errors.append("source.requirement_doc is required")
    elif not requirement_doc_path.exists():
        errors.append(f"requirement_doc does not exist: {requirement_doc_path}")
    elif not _inside_project(requirement_doc_path, project_root):
        errors.append(
            f"requirement_doc must be under the project root: {requirement_doc_path}"
        )
    else:
        doc_text = requirement_doc_path.read_text(encoding="utf-8", errors="replace")
        if len(doc_text.strip()) < 200:
            errors.append("requirement_doc is too short or appears to be a placeholder")
        for required_section in (
            "功能项清单",
            "平台依赖和数据来源",
            "澄清记录",
            "交接给 design-phase",
        ):
            if required_section not in doc_text:
                errors.append(f"requirement_doc missing section: {required_section}")
        if is_final and any(marker in doc_text for marker in PENDING_MARKERS):
            errors.append("final requirement_doc still contains pending markers")

    if not isinstance(requirement_items, list) or not requirement_items:
        errors.append("requirement_items must be a non-empty array")
        requirement_items = []

    if not isinstance(platform_tasks, list):
        errors.append("platform_dependency_tasks must be an array")
        platform_tasks = []

    if not isinstance(target_resolution, list):
        errors.append("target_object_resolution must be an array")
        target_resolution = []

    if not platform_tasks and not data.get("no_platform_dependency_reason"):
        warnings.append(
            "platform_dependency_tasks is empty; add no_platform_dependency_reason only when no platform dependency truly exists"
        )

    target_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for entry in target_resolution:
        if isinstance(entry, dict):
            key = str(entry.get("from_requirement") or "").strip()
            if key:
                target_by_requirement.setdefault(key, []).append(entry)

    for index, raw_item in enumerate(requirement_items, start=1):
        if not isinstance(raw_item, dict):
            errors.append(f"requirement_items[{index}] must be an object")
            continue

        item_id = str(raw_item.get("id") or "").strip()
        label = item_id or f"requirement_items[{index}]"
        title = raw_item.get("title") or raw_item.get("summary")

        for field_name in ("id", "priority", "evidence_level"):
            if not raw_item.get(field_name):
                errors.append(f"{label} missing required field: {field_name}")
        if not title:
            errors.append(f"{label} missing required field: title or summary")

        acceptance = _as_list(raw_item.get("acceptance_criteria"))
        business_rules = _as_list(raw_item.get("business_rules"))
        data_rules = _as_list(raw_item.get("data_rules"))
        exceptions = _as_list(
            raw_item.get("exceptions_or_boundaries") or raw_item.get("exceptions")
        )

        priority = str(raw_item.get("priority") or "").upper()
        min_acceptance = 5 if priority == "P0" else 4 if priority == "P1" else 1
        if len([item for item in acceptance if _text_blob(item).strip()]) < min_acceptance:
            errors.append(
                f"{label} has too few acceptance_criteria for {priority or 'unknown priority'}; expected at least {min_acceptance}"
            )
        if not [item for item in business_rules if _text_blob(item).strip()]:
            errors.append(f"{label} missing business_rules")
        if not [item for item in data_rules if _text_blob(item).strip()]:
            errors.append(f"{label} missing data_rules")
        if not [item for item in exceptions if _text_blob(item).strip()]:
            errors.append(f"{label} missing exceptions_or_boundaries")

        if _contains_target_action(raw_item):
            entries = target_by_requirement.get(item_id, []) if item_id else []
            if not entries and not _has_open_target_risk(item_id, data):
                errors.append(
                    f"{label} appears to involve notification/assignment/targeted delivery but has no target_object_resolution entry"
                )
            for entry in entries:
                missing = [
                    name
                    for name in (
                        "action",
                        "target_object",
                        "target_source",
                        "contact_or_identifier_source",
                        "permission_or_filter_rule",
                        "status",
                    )
                    if not entry.get(name)
                ]
                if missing:
                    errors.append(
                        f"{label} target_object_resolution entry missing fields: {', '.join(missing)}"
                    )
                if is_final and str(entry.get("status") or "").lower() in {
                    "open",
                    "pending",
                    "待确认",
                }:
                    errors.append(
                        f"{label} final handoff cannot keep target_object_resolution.status={entry.get('status')}"
                    )

    if is_final:
        if open_questions:
            errors.append("final handoff must not contain open_questions")
        critical_open_risks = [
            risk
            for risk in open_risks
            if isinstance(risk, dict)
            and str(risk.get("critical") or "").lower() in {"true", "yes", "1", "是"}
        ]
        if critical_open_risks:
            errors.append("final handoff must not contain critical open_risks_for_design")
        if "待确认" in _text_blob(data):
            errors.append("final handoff JSON still contains 待确认")

    return {
        "success": not errors,
        "errors": errors,
        "warnings": warnings,
        "checked_at": _now_iso(),
        "input": str(handoff_path),
        "project_root": str(project_root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate requirement-analysis handoff JSON."
    )
    parser.add_argument("--handoff", required=True, help="Path to requirement-handoff.json")
    parser.add_argument(
        "--output",
        help="Path to write validation JSON. Defaults to requirement-validation.json beside the handoff.",
    )
    parser.add_argument(
        "--project-root",
        help="Project root. Defaults to current working directory.",
    )
    args = parser.parse_args(argv)

    handoff_path = Path(args.handoff)
    output_path = (
        Path(args.output)
        if args.output
        else handoff_path.parent / "requirement-validation.json"
    )
    project_root = Path(args.project_root) if args.project_root else None

    result = validate(handoff_path, project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    node = sys.stdout
    json.dump(result, node, ensure_ascii=False, indent=2)
    node.write("\n")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
