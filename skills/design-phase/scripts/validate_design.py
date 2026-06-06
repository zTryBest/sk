#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate design-phase handoff JSON.

The design handoff is the machine-readable contract for later coding stages.
For baseline API reuse, this validator requires concrete API identity and
request/response details so implementation workers do not have to guess.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


PENDING_MARKERS = ("待确认", "[待确认]", "TBD", "TODO", "UNDECIDED")
API_MODES = {"BASELINE_API_REUSE", "HYBRID"}
CUSTOM_MODES = {"CUSTOM_CODE", "HYBRID"}
EXTERNAL_MODES = {"EXTERNAL_INTEGRATION", "HYBRID"}
VERSION_POLICIES = {"EXACT", "BACKWARD_COMPATIBLE", "MANUAL_MAPPING"}


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


def has_payload(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def api_has_request_contract(api: dict[str, Any]) -> bool:
    candidates = [
        api.get("request"),
        api.get("request_parameters"),
        api.get("request_params"),
        api.get("parameters"),
        api.get("headers"),
        api.get("path_params"),
        api.get("query_params"),
        api.get("body_schema"),
    ]
    return any(has_payload(candidate) for candidate in candidates)


def api_has_response_contract(api: dict[str, Any]) -> bool:
    candidates = [
        api.get("response"),
        api.get("response_result"),
        api.get("response_schema"),
        api.get("success_schema"),
        api.get("error_schema"),
        api.get("examples"),
    ]
    return any(has_payload(candidate) for candidate in candidates)


def parse_version(value: Any) -> tuple[int, ...] | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text[0] in {"v", "V"}:
        text = text[1:]
    parts: list[int] = []
    for raw in text.replace("_", ".").replace("-", ".").split("."):
        if raw == "":
            continue
        if not raw.isdigit():
            return None
        parts.append(int(raw))
    if not parts:
        return None
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def append_version_issue(errors: list[str], warnings: list[str], status: str, message: str) -> None:
    if status == "final":
        errors.append(message)
    else:
        warnings.append(message)


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
    status = str(source.get("design_status") or "").strip()
    if status not in {"final", "draft"}:
        errors.append("source.design_status must be final or draft")

    product = data.get("product")
    if not isinstance(product, dict):
        errors.append("product object is required")
        product = {}
    if is_blank(product.get("product_id")):
        errors.append("product.product_id is required")
    if is_blank(product.get("product_version")):
        errors.append("product.product_version is required")

    architecture = as_list(data.get("architecture_decisions"))
    if not architecture:
        errors.append("architecture_decisions must contain at least one item")
    for index, item in enumerate(architecture, start=1):
        if not isinstance(item, dict):
            errors.append(f"architecture_decisions[{index}] must be an object")
            continue
        if is_blank(item.get("item")) or is_blank(item.get("decision")):
            errors.append(f"architecture_decisions[{index}] needs item and decision")
        if status == "final" and item.get("confirmed") is not True:
            errors.append(f"architecture_decisions[{index}] must be confirmed for final design")

    classifications = as_list(data.get("implementation_classification"))
    if not classifications:
        errors.append("implementation_classification must contain at least one item")
    api_classifications: list[str] = []
    custom_classifications: list[str] = []
    external_classifications: list[str] = []
    for index, item in enumerate(classifications, start=1):
        if not isinstance(item, dict):
            errors.append(f"implementation_classification[{index}] must be an object")
            continue
        item_id = str(item.get("id") or f"#{index}")
        mode = str(item.get("mode") or "").strip()
        if is_blank(item.get("from_requirement")):
            errors.append(f"implementation_classification[{item_id}].from_requirement is required")
        if mode == "UNDECIDED":
            message = f"implementation_classification[{item_id}].mode is UNDECIDED"
            if status == "final":
                errors.append(message)
            else:
                warnings.append(message)
        if status == "final" and item.get("confirmed") is not True:
            errors.append(f"implementation_classification[{item_id}] must be confirmed for final design")
        if mode in API_MODES:
            api_classifications.append(item_id)
        if mode in CUSTOM_MODES:
            custom_classifications.append(item_id)
        if mode in EXTERNAL_MODES:
            external_classifications.append(item_id)

    mcp_plan = as_list(data.get("mcp_search_plan"))
    mcp_log = as_list(data.get("mcp_call_log"))
    if api_classifications:
        if not mcp_plan:
            errors.append("BASELINE_API_REUSE/HYBRID classifications require mcp_search_plan")
        if not mcp_log:
            errors.append("BASELINE_API_REUSE/HYBRID classifications require mcp_call_log")

    selected_apis = as_list(data.get("selected_baseline_apis"))
    if api_classifications and not selected_apis:
        errors.append("BASELINE_API_REUSE/HYBRID classifications require selected_baseline_apis")
    for index, api in enumerate(selected_apis, start=1):
        if not isinstance(api, dict):
            errors.append(f"selected_baseline_apis[{index}] must be an object")
            continue
        label = api.get("api_path") or api.get("task_id") or f"#{index}"
        for field in ("method", "api_path"):
            if is_blank(api.get(field)):
                errors.append(f"selected_baseline_apis[{label}].{field} is required")
        if api.get("get_api_detail_called") is not True:
            errors.append(f"selected_baseline_apis[{label}].get_api_detail_called must be true")
        if not api_has_request_contract(api):
            errors.append(f"selected_baseline_apis[{label}] is missing request parameters/contract")
        if not api_has_response_contract(api):
            errors.append(f"selected_baseline_apis[{label}] is missing response result/contract")
        resolved_doc_version = str(api.get("resolved_doc_version") or "").strip()
        contract_doc_version = str(api.get("contract_doc_version") or "").strip()
        version_compatibility = str(api.get("version_compatibility") or "").strip()
        version_policy = str(api.get("version_match_policy") or "").strip()
        if not resolved_doc_version:
            append_version_issue(errors, warnings, status, f"selected_baseline_apis[{label}].resolved_doc_version is required")
        if not contract_doc_version:
            append_version_issue(errors, warnings, status, f"selected_baseline_apis[{label}].contract_doc_version is required")
        if version_compatibility != "PASS":
            append_version_issue(errors, warnings, status, f"selected_baseline_apis[{label}].version_compatibility must be PASS")
        if version_policy and version_policy not in VERSION_POLICIES:
            append_version_issue(errors, warnings, status, f"selected_baseline_apis[{label}].version_match_policy is invalid")
        if not version_policy:
            append_version_issue(errors, warnings, status, f"selected_baseline_apis[{label}].version_match_policy is required")
        if resolved_doc_version and contract_doc_version:
            resolved_version = parse_version(resolved_doc_version)
            contract_version = parse_version(contract_doc_version)
            if resolved_version is None:
                append_version_issue(errors, warnings, status, f"selected_baseline_apis[{label}].resolved_doc_version is not comparable")
            if contract_version is None:
                append_version_issue(errors, warnings, status, f"selected_baseline_apis[{label}].contract_doc_version is not comparable")
            if resolved_version is not None and contract_version is not None and contract_version > resolved_version:
                errors.append(
                    f"selected_baseline_apis[{label}] uses higher contract_doc_version {contract_doc_version} "
                    f"than resolved_doc_version {resolved_doc_version}"
                )

    custom_design = as_list(data.get("custom_implementation"))
    if custom_classifications and not custom_design:
        errors.append("CUSTOM_CODE/HYBRID classifications require custom_implementation")

    external_design = as_list(data.get("external_integrations"))
    if external_classifications and not external_design:
        errors.append("EXTERNAL_INTEGRATION/HYBRID classifications require external_integrations")

    if status == "final" and contains_marker(data):
        errors.append("final design handoff contains pending markers")

    return {
        "success": not errors,
        "checked_at": now_iso(),
        "validator": "design-phase/scripts/validate_design.py",
        "handoff": str(handoff_path),
        "project_root": project_root,
        "design_status": status or "",
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Validate design-phase handoff JSON.")
    parser.add_argument("--handoff", required=True, help="Path to design-handoff.json")
    parser.add_argument("--output", required=True, help="Path to design-validation.json")
    parser.add_argument("--project-root", default="", help="Project root path for traceability")
    args = parser.parse_args()

    handoff_path = Path(args.handoff).resolve()
    output_path = Path(args.output).resolve()
    if not handoff_path.exists():
        result = {
            "success": False,
            "checked_at": now_iso(),
            "validator": "design-phase/scripts/validate_design.py",
            "handoff": str(handoff_path),
            "project_root": args.project_root,
            "design_status": "",
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
            "validator": "design-phase/scripts/validate_design.py",
            "handoff": str(handoff_path),
            "project_root": args.project_root,
            "design_status": "",
            "errors": [f"invalid JSON: {exc}"],
            "warnings": [],
        }

    write_json(output_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
