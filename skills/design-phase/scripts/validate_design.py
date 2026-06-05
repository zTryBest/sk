#!/usr/bin/env python3
"""Validate design-phase handoff artifacts.

The design validator enforces the handoff contract that later prototype,
coding, and self-test phases should consume. It focuses on step preservation:
classification, MCP transparency, API-detail confirmation, and separate custom
versus external integration design.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


IMPLEMENTATION_MODES = {
    "BASELINE_API_REUSE",
    "CUSTOM_CODE",
    "EXTERNAL_INTEGRATION",
    "HYBRID",
    "NO_API_NEEDED",
    "UNDECIDED",
}

MCP_DECISIONS = {
    "PENDING_USER_CHOICE",
    "SELECTED",
    "REJECTED_SCENE_MISMATCH",
    "REJECTED_FIELD_GAP",
    "REJECTED_RISK",
    "NO_CANDIDATE",
    "NEED_KB_IMPORT",
}

FINAL_STATUS_VALUES = {"final", "最终版", "正式版"}
PENDING_MARKERS = ("[待确认]", "待确认", "UNDECIDED")


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


def _inside_project(path: Path, project_root: Path) -> bool:
    try:
        path.resolve().relative_to(project_root.resolve())
        return True
    except ValueError:
        return False


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


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "yes", "1", "是", "已确认"}


def _index_by(items: list[Any], key: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        value = str(item.get(key) or "").strip()
        if value:
            result.setdefault(value, []).append(item)
    return result


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
    classifications = data.get("implementation_classification")
    mcp_plan = data.get("mcp_search_plan")
    mcp_log = data.get("mcp_call_log")
    selected_apis = data.get("selected_baseline_apis")
    custom_impl = data.get("custom_implementation")
    external_integrations = data.get("external_integrations")
    architecture_decisions = data.get("architecture_decisions")
    open_risks = _as_list(data.get("open_risks"))
    design_status = source.get("design_status")
    is_final = _is_final_status(design_status)

    for field_name, value in (
        ("source.requirement_handoff", source.get("requirement_handoff")),
        ("source.design_doc", source.get("design_doc")),
        ("source.design_status", design_status),
        ("product.product_id", product.get("product_id")),
        ("product.product_version", product.get("product_version")),
    ):
        if not value:
            errors.append(f"missing required field: {field_name}")

    for path_field in ("requirement_handoff", "requirement_doc", "design_doc"):
        path_value = source.get(path_field)
        if not path_value:
            continue
        resolved = _resolve_path(path_value, base_dir)
        if resolved is None:
            continue
        if not resolved.exists():
            errors.append(f"source.{path_field} does not exist: {resolved}")
        elif not _inside_project(resolved, project_root):
            errors.append(f"source.{path_field} must be under project root: {resolved}")

    design_doc_path = _resolve_path(source.get("design_doc"), base_dir)
    if design_doc_path and design_doc_path.exists():
        doc_text = design_doc_path.read_text(encoding="utf-8", errors="replace")
        if len(doc_text.strip()) < 300:
            errors.append("design_doc is too short or appears to be a placeholder")
        for required_section in (
            "实现方式总表",
            "MCP 检索和证据表",
            "MCP 调用记录",
            "定制实现表",
            "外部集成表",
        ):
            if required_section not in doc_text:
                errors.append(f"design_doc missing section: {required_section}")
        if is_final and any(marker in doc_text for marker in PENDING_MARKERS):
            errors.append("final design_doc still contains pending markers")

    if not isinstance(architecture_decisions, list) or not architecture_decisions:
        errors.append("architecture_decisions must be a non-empty array")
        architecture_decisions = []
    elif is_final:
        for index, decision in enumerate(architecture_decisions, start=1):
            if not isinstance(decision, dict):
                errors.append(f"architecture_decisions[{index}] must be an object")
                continue
            if not decision.get("item") or not decision.get("decision"):
                errors.append(
                    f"architecture_decisions[{index}] must include item and decision"
                )
            if not _truthy(decision.get("confirmed")):
                errors.append(
                    f"architecture_decisions[{index}] must be confirmed for final design"
                )

    list_fields = {
        "implementation_classification": classifications,
        "mcp_search_plan": mcp_plan,
        "mcp_call_log": mcp_log,
        "selected_baseline_apis": selected_apis,
        "custom_implementation": custom_impl,
        "external_integrations": external_integrations,
    }
    for field_name, value in list_fields.items():
        if not isinstance(value, list):
            errors.append(f"{field_name} must be an array")
            list_fields[field_name] = []

    classifications = list_fields["implementation_classification"]
    mcp_plan = list_fields["mcp_search_plan"]
    mcp_log = list_fields["mcp_call_log"]
    selected_apis = list_fields["selected_baseline_apis"]
    custom_impl = list_fields["custom_implementation"]
    external_integrations = list_fields["external_integrations"]

    if not classifications:
        errors.append("implementation_classification must be non-empty")

    plan_by_classification = _index_by(mcp_plan, "from_classification")
    log_by_task = _index_by(mcp_log, "task_id")
    custom_by_classification = _index_by(custom_impl, "from_classification")
    external_by_classification = _index_by(external_integrations, "from_classification")

    classification_ids: set[str] = set()
    for index, item in enumerate(classifications, start=1):
        if not isinstance(item, dict):
            errors.append(f"implementation_classification[{index}] must be an object")
            continue
        classification_id = str(item.get("id") or "").strip()
        label = classification_id or f"implementation_classification[{index}]"
        classification_ids.add(classification_id)
        mode = str(item.get("mode") or "").strip()

        for field_name in ("id", "from_requirement", "sub_capability", "mode", "rationale"):
            if not item.get(field_name):
                errors.append(f"{label} missing required field: {field_name}")

        if mode not in IMPLEMENTATION_MODES:
            errors.append(f"{label} has invalid mode: {mode}")
        if is_final and mode == "UNDECIDED":
            errors.append(f"{label} cannot remain UNDECIDED in final design")
        if is_final and not _truthy(item.get("confirmed")):
            errors.append(f"{label} must be confirmed in final design")

        if mode in {"BASELINE_API_REUSE", "HYBRID"}:
            if not plan_by_classification.get(classification_id):
                errors.append(
                    f"{label} is {mode} but has no mcp_search_plan entry"
                )
        if mode in {"CUSTOM_CODE", "HYBRID"}:
            if not custom_by_classification.get(classification_id):
                errors.append(
                    f"{label} is {mode} but has no custom_implementation entry"
                )
        if mode == "EXTERNAL_INTEGRATION":
            if not external_by_classification.get(classification_id):
                errors.append(
                    f"{label} is EXTERNAL_INTEGRATION but has no external_integrations entry"
                )

    for index, task in enumerate(mcp_plan, start=1):
        if not isinstance(task, dict):
            errors.append(f"mcp_search_plan[{index}] must be an object")
            continue
        task_id = str(task.get("task_id") or "").strip()
        label = task_id or f"mcp_search_plan[{index}]"
        for field_name in ("task_id", "from_classification", "query"):
            if not task.get(field_name):
                errors.append(f"{label} missing required field: {field_name}")
        if task.get("from_classification") and task.get("from_classification") not in classification_ids:
            warnings.append(
                f"{label} references unknown classification: {task.get('from_classification')}"
            )
        if _truthy(task.get("must_search")) and not log_by_task.get(task_id):
            errors.append(f"{label} has must_search=true but no mcp_call_log entry")
        query = str(task.get("query") or "")
        if any(word in query for word in ("发送短信", "调用第三方", "外部系统", "SOAP发送")):
            warnings.append(
                f"{label} query may describe an external action instead of platform context: {query}"
            )

    for index, log in enumerate(mcp_log, start=1):
        if not isinstance(log, dict):
            errors.append(f"mcp_call_log[{index}] must be an object")
            continue
        label = str(log.get("task_id") or f"mcp_call_log[{index}]")
        for field_name in ("task_id", "tool", "request", "candidate_count", "decision", "reason"):
            if field_name not in log or log.get(field_name) in (None, ""):
                errors.append(f"{label} missing required field: {field_name}")
        if log.get("tool") != "find_apis_for_requirement":
            warnings.append(
                f"{label} should normally use find_apis_for_requirement; got {log.get('tool')}"
            )
        if str(log.get("decision") or "") not in MCP_DECISIONS:
            errors.append(f"{label} has invalid decision: {log.get('decision')}")

    for index, api in enumerate(selected_apis, start=1):
        if not isinstance(api, dict):
            errors.append(f"selected_baseline_apis[{index}] must be an object")
            continue
        label = str(api.get("task_id") or f"selected_baseline_apis[{index}]")
        for field_name in (
            "task_id",
            "component_id",
            "segment_id",
            "component_version",
            "method",
            "api_path",
            "doc_version",
        ):
            if not api.get(field_name):
                errors.append(f"{label} selected API missing field: {field_name}")
        if not _truthy(api.get("get_api_detail_called")):
            errors.append(
                f"{label} selected API must set get_api_detail_called=true"
            )

    for index, impl in enumerate(custom_impl, start=1):
        if not isinstance(impl, dict):
            errors.append(f"custom_implementation[{index}] must be an object")
            continue
        label = str(impl.get("from_classification") or f"custom_implementation[{index}]")
        for field_name in (
            "from_classification",
            "module",
            "responsibility",
            "error_handling",
            "test_points",
        ):
            value = impl.get(field_name)
            if value in (None, "") or (isinstance(value, list) and not value):
                errors.append(f"{label} custom implementation missing field: {field_name}")

    for index, integration in enumerate(external_integrations, start=1):
        if not isinstance(integration, dict):
            errors.append(f"external_integrations[{index}] must be an object")
            continue
        label = str(
            integration.get("from_classification") or f"external_integrations[{index}]"
        )
        for field_name in (
            "from_classification",
            "system",
            "protocol",
            "auth",
            "request_response",
            "timeout_retry",
            "callback_or_receipt",
            "fallback",
        ):
            if not integration.get(field_name):
                errors.append(f"{label} external integration missing field: {field_name}")

    if is_final:
        critical_open_risks = [
            risk
            for risk in open_risks
            if isinstance(risk, dict)
            and str(risk.get("critical") or "").lower() in {"true", "yes", "1", "是"}
        ]
        if critical_open_risks:
            errors.append("final design handoff must not contain critical open_risks")
        if any(marker in _text_blob(data) for marker in PENDING_MARKERS):
            errors.append("final design handoff still contains pending markers")

    return {
        "success": not errors,
        "errors": errors,
        "warnings": warnings,
        "checked_at": _now_iso(),
        "input": str(handoff_path),
        "project_root": str(project_root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate design-phase handoff JSON.")
    parser.add_argument("--handoff", required=True, help="Path to design-handoff.json")
    parser.add_argument(
        "--output",
        help="Path to write validation JSON. Defaults to design-validation.json beside the handoff.",
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
        else handoff_path.parent / "design-validation.json"
    )
    project_root = Path(args.project_root) if args.project_root else None

    result = validate(handoff_path, project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
