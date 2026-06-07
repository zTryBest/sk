#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight orchestrator state helper for Claude Code worker workflows."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


configure_stdio()


STAGES = [
    "requirement-analysis",
    "design-phase",
]
DEFAULT_MANUAL_CONFIRMATION_STAGES = ["requirement-analysis"]

VALIDATION_BY_STAGE = {
    "requirement-analysis": "requirement-validation.json",
    "design-phase": "design-validation.json",
}

HANDOFF_BY_STAGE = {
    "requirement-analysis": "requirement-handoff.json",
    "design-phase": "design-handoff.json",
}

DEFAULT_WORKER_PERMISSION_MODE = "acceptEdits"
DEFAULT_WORKER_ALLOWED_TOOLS = ",".join([
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Glob",
    "Grep",
    "LS",
    "WebFetch",
    "WebSearch",
    "mcp__playwright",
    "mcp__browser",
    "mcp__browser_use",
    "Bash(python *)",
    "Bash(py *)",
])

DEFAULT_AUTO_DECISION_ALLOWED_TOOLS = ",".join([
    "Read",
    "Glob",
    "Grep",
    "LS",
])

EXTERNAL_ACTION_REQUIRES_MAIN_SESSION = {
    "BROWSER_LOGIN",
    "HUMAN_VERIFICATION",
    "FILE_SELECTION",
    "EXTERNAL_SYSTEM_OPERATION",
}

DEFAULT_MAX_MISSING_RESULT_RECOVERIES = 2

DEFAULT_WORKER_SUBAGENTS = {
    "workflow-requirement-researcher": {
        "description": "Read-only researcher for requirement-analysis. Use for high-volume ticket, document, web, or codebase exploration that would flood the worker context.",
        "prompt": (
            "You are a read-only requirement research subagent inside a workflow worker. "
            "Gather relevant facts, evidence paths, URLs, and unresolved questions. "
            "Do not edit or write files. Do not ask the user. Return a concise summary with evidence and open issues for the parent worker to decide."
        ),
        "tools": ["Read", "Glob", "Grep", "LS", "WebFetch", "WebSearch"],
        "model": "inherit",
        "permissionMode": "default",
        "maxTurns": 12,
    },
    "workflow-design-researcher": {
        "description": "Read-only researcher for design-phase. Use for API, platform context, dependency, and implementation-option exploration.",
        "prompt": (
            "You are a read-only design research subagent inside a workflow worker. "
            "Inspect only the requested sources and return concise findings, candidate APIs, evidence paths, and uncertainty. "
            "Do not edit or write files. Do not ask the user. The parent worker owns the design document and all final decisions."
        ),
        "tools": ["Read", "Glob", "Grep", "LS", "WebFetch", "WebSearch"],
        "model": "inherit",
        "permissionMode": "default",
        "maxTurns": 12,
    },
    "workflow-risk-reviewer": {
        "description": "Read-only reviewer for design-phase risks, missing decisions, and validation readiness.",
        "prompt": (
            "You are a read-only risk review subagent inside a workflow worker. "
            "Review the provided requirement/design context for contradictions, missing decisions, validation risks, and user-confirmation needs. "
            "Do not edit or write files. Do not ask the user. Return only a concise risk list and recommended parent-worker actions."
        ),
        "tools": ["Read", "Glob", "Grep", "LS"],
        "model": "inherit",
        "permissionMode": "default",
        "maxTurns": 8,
    },
}

STAGE_WORKER_SUBAGENTS = {
    "requirement-analysis": ["workflow-requirement-researcher"],
    "design-phase": ["workflow-design-researcher", "workflow-risk-reviewer"],
}


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False) + "\n")


def append_jsonl_all(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                rows.append(data)
    return rows


def copy_if_exists(src: Path, dest: Path) -> None:
    if src.exists() and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def resolve_project_root(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    return Path.cwd().resolve()


def bundled_skills_root() -> Path:
    return Path(__file__).resolve().parents[2]


def user_claude_config_dir() -> Path:
    return Path.home() / ".claude" / "config"


def resolve_stage_skill(project_root: Path, stage: str) -> Path:
    candidates = [
        project_root / ".claude" / "skills" / stage / "SKILL.md",
        bundled_skills_root() / stage / "SKILL.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def env_truthy(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def stage_subagent_names(stage: str) -> list[str]:
    return list(STAGE_WORKER_SUBAGENTS.get(stage, []))


def subagent_definitions_for(names: list[str]) -> dict[str, Any]:
    return {
        name: DEFAULT_WORKER_SUBAGENTS[name]
        for name in names
        if name in DEFAULT_WORKER_SUBAGENTS
    }


def default_artifact_dir(project_root: Path, run_id: str) -> Path:
    return project_root / "requirements" / "_workflow" / run_id


def state_path_from_artifact(artifact_dir: Path) -> Path:
    return artifact_dir / "workflow-state.json"


def last_state_pointer_path(project_root: Path | None = None) -> Path:
    root = (project_root or Path.cwd()).resolve()
    return root / ".claude" / "workflow-orchestrator-last-state.json"


def write_last_state_pointer(project_root: Path, state_path: Path, artifact_dir: Path) -> None:
    write_json(last_state_pointer_path(project_root), {
        "schema_version": "1.0",
        "state": str(state_path.resolve()),
        "artifact_dir": str(artifact_dir.resolve()),
        "updated_at": now_iso(),
    })


def resolve_state_path(value: str | None = None, artifact_dir: str | None = None) -> Path:
    if value:
        return Path(value).resolve()
    if artifact_dir:
        candidate = Path(artifact_dir).resolve()
        if candidate.is_dir():
            return candidate / "workflow-state.json"
        return candidate.resolve()
    cwd_candidate = Path.cwd() / "workflow-state.json"
    if cwd_candidate.exists():
        return cwd_candidate.resolve()
    pointer = read_json(last_state_pointer_path(), {})
    if isinstance(pointer, dict) and pointer.get("state"):
        state_candidate = Path(str(pointer["state"])).resolve()
        if state_candidate.exists():
            return state_candidate
    workflow_dirs = sorted(
        (Path.cwd() / "requirements" / "_workflow").glob("*/workflow-state.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if (Path.cwd() / "requirements" / "_workflow").exists() else []
    if workflow_dirs:
        return workflow_dirs[0].resolve()
    raise SystemExit("workflow state is required. Pass --state <workflow-state.json> or --artifact-dir/--artifacts-dir <artifact dir>.")


def build_initial_input(args: argparse.Namespace) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    if getattr(args, "url", None):
        sources.append({"type": "ticket_url", "value": args.url})
    if getattr(args, "input_text", None):
        sources.append({"type": "manual_text", "content": args.input_text})
    if getattr(args, "input_file", None):
        sources.append({"type": "document_file", "path": str(Path(args.input_file).expanduser().resolve())})

    requested_type = getattr(args, "source_type", "auto") or "auto"
    if requested_type == "ticket_url" and not any(source.get("type") == "ticket_url" for source in sources):
        raise SystemExit("--source-type ticket_url requires --url or --ticket-url")
    if requested_type == "document_file" and not any(source.get("type") == "document_file" for source in sources):
        raise SystemExit("--source-type document_file requires --input-file or --document")
    if requested_type in {"manual_text", "goal_only"} and not sources:
        sources.append({"type": "manual_text", "content": args.goal or "", "from": "goal"})

    if requested_type != "auto":
        source_type = requested_type
    elif len(sources) > 1:
        source_type = "mixed"
    elif sources:
        source_type = sources[0]["type"]
    else:
        source_type = "goal_only"
        sources.append({"type": "manual_text", "content": args.goal or "", "from": "goal"})

    return {
        "schema_version": "1.0",
        "source_type": source_type,
        "goal": args.goal or default_goal_for_sources(sources, source_type),
        "sources": sources,
        "created_at": now_iso(),
    }


def default_goal_for_sources(sources: list[dict[str, Any]], source_type: str) -> str:
    if any(source.get("type") == "ticket_url" for source in sources):
        return "从需求单 URL 提取需求并执行工作流"
    if any(source.get("type") == "document_file" for source in sources):
        return "从需求文档提取需求并执行工作流"
    if any(source.get("type") == "manual_text" and str(source.get("content") or "").strip() for source in sources):
        return "根据用户提供的需求描述执行工作流"
    if source_type == "goal_only":
        return "根据用户目标执行工作流"
    return "执行需求分析和方案设计工作流"


def source_signature(initial_input: dict[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for source in initial_input.get("sources", []):
        if not isinstance(source, dict):
            continue
        normalized = {key: source.get(key) for key in sorted(source) if key not in {"created_at"}}
        sources.append(normalized)
    return {
        "source_type": initial_input.get("source_type", ""),
        "sources": sources,
    }


def same_initial_source(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return source_signature(a) == source_signature(b)


def find_reusable_workflow(project_root: Path, initial_input: dict[str, Any], stage: str) -> Path | None:
    workflow_root = project_root / "requirements" / "_workflow"
    if not workflow_root.exists():
        return None
    state_paths = sorted(
        workflow_root.glob("*/workflow-state.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    reusable_statuses = {"READY", "NEED_USER_INPUT", "VALIDATION_FAILED", "RUNNING"}
    for state_path in state_paths:
        state = read_json(state_path, {})
        if not isinstance(state, dict):
            continue
        if state.get("current_stage") != stage:
            continue
        if state.get("stage_status") not in reusable_statuses:
            continue
        existing_input = read_json(state_path.parent / state.get("workflow_input", "workflow-input.json"), {})
        if isinstance(existing_input, dict) and same_initial_source(existing_input, initial_input):
            return state_path.resolve()
    return None


def initial_input_path(state: dict[str, Any]) -> Path:
    return Path(state["artifact_dir"]) / state.get("workflow_input", "workflow-input.json")


def input_access_dirs(state: dict[str, Any]) -> list[Path]:
    data = read_json(initial_input_path(state), {})
    if not isinstance(data, dict):
        return []
    dirs: list[Path] = []
    for source in data.get("sources", []):
        if not isinstance(source, dict) or source.get("type") != "document_file":
            continue
        path_text = source.get("path")
        if not path_text:
            continue
        path = Path(path_text).expanduser()
        if path.exists():
            dirs.append(path.resolve().parent)
    return dirs


def load_state(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"workflow state not found or invalid: {path}")
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    write_json(path, state)


def add_history(state: dict[str, Any], event: str, detail: dict[str, Any] | None = None) -> None:
    history = state.setdefault("history", [])
    history.append({"at": now_iso(), "event": event, "detail": detail or {}})


def parse_stage_list(value: str | None) -> list[str]:
    if not value:
        return []
    stages: list[str] = []
    for raw in value.replace(";", ",").split(","):
        stage = raw.strip()
        if not stage:
            continue
        if stage not in STAGES:
            raise SystemExit(f"unknown stage in confirmation policy: {stage}; allowed: {', '.join(STAGES)}")
        if stage not in stages:
            stages.append(stage)
    return stages


def confirmation_policy_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.full_auto or args.auto_confirm:
        manual_stages: list[str] = []
        policy = "full_auto" if args.full_auto else "ai_all"
    else:
        manual_stages = list(DEFAULT_MANUAL_CONFIRMATION_STAGES)
        policy = "default"

    explicit_manual = parse_stage_list(getattr(args, "manual_confirm_stages", None))
    explicit_ai = parse_stage_list(getattr(args, "ai_confirm_stages", None))
    if explicit_manual:
        manual_stages = explicit_manual
        policy = "custom"
    for stage in explicit_ai:
        if stage in manual_stages:
            manual_stages.remove(stage)
            policy = "custom"

    return {
        "stage_confirmation_policy": policy,
        "manual_confirmation_stages": manual_stages,
        "ai_confirmation_stages": [stage for stage in STAGES if stage not in manual_stages],
    }


def confirmation_args_explicit(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "full_auto", False)
        or getattr(args, "auto_confirm", False)
        or getattr(args, "manual_confirm_stages", None)
        or getattr(args, "ai_confirm_stages", None)
    )


def apply_confirmation_policy(state: dict[str, Any], policy: dict[str, Any], *, full_auto: bool, auto_confirm: bool) -> None:
    state["stage_confirmation_policy"] = policy["stage_confirmation_policy"]
    state["manual_confirmation_stages"] = policy["manual_confirmation_stages"]
    state["ai_confirmation_stages"] = policy["ai_confirmation_stages"]
    state["full_auto"] = bool(full_auto)
    state["auto_confirm_mode"] = "ai" if full_auto or auto_confirm else "per_stage"


def pending_confirmation_stage(state: dict[str, Any]) -> str:
    return str(state.get("completed_stage_waiting_approval") or state.get("current_stage") or "")


def ai_confirmation_enabled_for_state(state: dict[str, Any], *, force_full_auto: bool = False) -> bool:
    if force_full_auto or state.get("full_auto") or state.get("auto_confirm_mode") == "ai":
        return True
    stage = pending_confirmation_stage(state)
    manual_stages = state.get("manual_confirmation_stages")
    if not isinstance(manual_stages, list):
        manual_stages = list(DEFAULT_MANUAL_CONFIRMATION_STAGES)
    return stage not in {str(item) for item in manual_stages}


def unique_paths(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path.absolute()
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(resolved)
    return unique


def newest_mtime(paths: list[Path]) -> float:
    mtimes: list[float] = []
    for path in paths:
        try:
            if path.exists():
                mtimes.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(mtimes) if mtimes else 0.0


def candidate_output_dirs(state: dict[str, Any]) -> list[Path]:
    project_root = Path(state.get("project_root") or ".").resolve()
    artifact_dir = Path(state.get("artifact_dir") or ".").resolve()
    candidates = [artifact_dir]
    for key in ("latest_handoff", "latest_validation"):
        value = state.get(key)
        if value:
            try:
                candidates.append(Path(str(value)).resolve().parent)
            except OSError:
                pass
    requirements_dir = project_root / "requirements"
    if requirements_dir.exists():
        try:
            children = [path for path in requirements_dir.iterdir() if path.is_dir() and path.name != "_workflow"]
        except OSError:
            children = []
        children.sort(key=lambda path: newest_mtime(list(path.glob("*"))), reverse=True)
        candidates.extend(children[:40])
    return unique_paths(candidates)


def partial_finalize_signature(candidate: dict[str, Any]) -> str:
    missing = ",".join(candidate.get("missing_outputs", []))
    return f"finalize:{candidate.get('stage', '')}:{candidate.get('directory', '')}:{missing}"


def find_partial_finalize_candidate(state: dict[str, Any]) -> dict[str, Any] | None:
    stage = state.get("current_stage")
    if stage == "requirement-analysis":
        evidence_names = ["需求分析-草稿.md", "需求分析.md", "design-phase-handoff.md", "requirement-handoff.json"]
        required_names = ["requirement-handoff.json", "requirement-validation.json"]
        validator = "requirement-analysis/scripts/validate_requirement.py"
    elif stage == "design-phase":
        evidence_names = ["design-doc.md", "design-handoff.json", "design-phase-state.md"]
        required_names = ["design-handoff.json", "design-validation.json"]
        validator = "design-phase/scripts/validate_design.py"
    else:
        return None

    artifact_dir = Path(state.get("artifact_dir") or ".").resolve()
    result_path = artifact_dir / "worker-result.json"
    candidates: list[dict[str, Any]] = []
    for directory in candidate_output_dirs(state):
        existing = [directory / name for name in evidence_names if (directory / name).exists()]
        if not existing:
            continue
        missing = [str(directory / name) for name in required_names if not (directory / name).exists()]
        if not result_path.exists():
            missing.append(str(result_path))
        if not missing:
            continue
        handoff_name = required_names[0]
        validation_name = required_names[1]
        candidate = {
            "stage": stage,
            "directory": str(directory),
            "existing_files": [str(path) for path in existing],
            "missing_outputs": missing,
            "handoff": str(directory / handoff_name),
            "validation": str(directory / validation_name),
            "validator": validator,
            "worker_result": str(result_path),
            "detected_at": now_iso(),
            "_mtime": newest_mtime(existing),
        }
        candidates.append(candidate)

    if not candidates:
        return None
    candidates.sort(key=lambda item: item.get("_mtime", 0.0), reverse=True)
    selected = dict(candidates[0])
    selected.pop("_mtime", None)
    return selected


def make_finalize_recovery_notes(state: dict[str, Any], result_path: Path) -> str:
    candidate = state.get("recovery_finalize")
    if not isinstance(candidate, dict):
        return ""
    stage = state.get("current_stage", "")
    project_root = Path(state.get("project_root") or ".").resolve()
    stage_skill_dir = resolve_stage_skill(project_root, stage).parent
    directory = candidate.get("directory", "")
    existing_files = "\n".join(f"- {path}" for path in candidate.get("existing_files", [])) or "- (none)"
    missing_outputs = "\n".join(f"- {path}" for path in candidate.get("missing_outputs", [])) or "- (none)"
    validator = candidate.get("validator", "")
    handoff = candidate.get("handoff", "")
    validation = candidate.get("validation", "")
    if stage == "requirement-analysis":
        validator_script = stage_skill_dir / "scripts" / "validate_requirement.py"
        stage_steps = f"""
- 只读取已有的需求草稿 / design-phase-handoff 和 requirement-analysis 的 output-contracts，不要重新抓取 URL、不要重跑完整需求分析。
- 先补齐或修正 `{handoff}`。如果仍有 open questions，`source.requirement_status` 必须是 `draft`，并把问题写入 `open_questions`。
- 运行：`python "{validator_script}" --handoff "{handoff}" --output "{validation}" --project-root "{project_root}"`
- 如果仍是草稿或存在 open questions，写 pending-questions.json 和 `{result_path}`，status=NEED_USER_INPUT。
- 如果已经是 final 且 validation success=true，写 `{result_path}`，status=STAGE_COMPLETED。
"""
    elif stage == "design-phase":
        validator_script = stage_skill_dir / "scripts" / "validate_design.py"
        stage_steps = f"""
- 只读取已有 design-doc/design-handoff 草稿和 design-phase 的 output-contracts，不要重新执行完整 Phase 0-9，除非缺少的字段无法从已有产物恢复。
- 补齐或修正 `{handoff}`。凡是选中的基线 API，必须包含 `method`、`api_path`、`get_api_detail_called=true`、请求参数/契约、响应结果/契约、`resolved_doc_version`、`contract_doc_version`、`version_match_policy` 和 `version_compatibility=PASS`。禁止低版本组件采纳高版本 API 契约。
- 运行：`python "{validator_script}" --handoff "{handoff}" --output "{validation}" --project-root "{project_root}"`
- 如果缺少 API 选择、架构决策、数据库类型或其他用户决策，写 pending-questions.json 和 `{result_path}`，status=NEED_USER_INPUT。
- 如果 validation success=true，写 `{result_path}`，status=STAGE_COMPLETED。
"""
    else:
        stage_steps = "- 当前阶段没有 finalize-recovery 规则，写 BLOCKED result。\n"
    return f"""
RECOVERY_FINALIZE_MODE:
上一次 worker 已经写出部分阶段产物，但没有写出可被 orchestrator 记录的 worker-result.json。当前 worker 只做收尾，不重跑完整阶段。

已有产物：
{existing_files}

缺失或需要确认的输出：
{missing_outputs}

收尾目录：{directory}
validator: {validator}
worker-result 必须写到：{result_path}
worker-result.artifact_dir 必须写为：{directory}

收尾规则：
{stage_steps}
"""


def write_stage_boundary_questions(
    artifact_dir: Path,
    *,
    completed_stage: str,
    next_stage_name: str,
    handoff: str,
    validation: str,
) -> Path:
    pending_path = artifact_dir / "pending-questions.json"
    question_batch_id = f"Q-{_dt.datetime.now().strftime('%Y%m%d%H%M%S')}-stage-boundary"
    write_json(pending_path, {
        "status": "NEED_USER_INPUT",
        "stage": completed_stage,
        "phase": "stage-boundary",
        "question_batch_id": question_batch_id,
        "questions": [
            {
                "id": f"workflow.advance_to.{next_stage_name}",
                "question": f"{completed_stage} 已完成且校验通过。是否确认进入 {next_stage_name}？",
                "options": [
                    {
                        "key": "approve",
                        "label": f"进入 {next_stage_name}",
                        "recommended": True,
                        "description": "确认当前阶段产物可作为下一阶段输入。",
                    },
                    {
                        "key": "revise",
                        "label": "返回修改",
                        "recommended": False,
                        "description": "补充修改意见后，重新运行当前阶段 worker。",
                    },
                    {
                        "key": "stop",
                        "label": "暂停流程",
                        "recommended": False,
                        "description": "保留当前产物，暂不进入下一阶段。",
                    },
                ],
                "impact": "下一阶段会基于当前阶段 handoff 和 validation 继续执行。",
                "default_if_full_auto": "approve",
            }
        ],
        "known_facts": [
            f"completed_stage={completed_stage}",
            f"next_stage={next_stage_name}",
            f"handoff={handoff}",
            f"validation={validation}",
        ],
        "blocking_reason": "等待用户确认阶段边界，避免在需求未确认时提前进入方案设计。",
    })
    return pending_path


def make_worker_prompt(state: dict[str, Any]) -> str:
    project_root = Path(state["project_root"])
    artifact_dir = Path(state["artifact_dir"])
    stage = state["current_stage"]
    decisions_log = artifact_dir / state.get("decisions_log", "decisions.jsonl")
    workflow_goal = state.get("workflow_goal", "")
    workflow_input = initial_input_path(state)

    prior_handoff = state.get("latest_handoff") or ""
    stage_skill = resolve_stage_skill(project_root, stage)
    result_path = artifact_dir / "worker-result.json"
    pending_path = artifact_dir / "pending-questions.json"
    state_path = artifact_dir / "workflow-state.json"

    if stage not in set(STAGES):
        return f"""worker_mode: true
stage: {stage}
artifact_dir: {artifact_dir}

当前阶段尚未实现对应 Claude Code skill 或 validator。
请只写 {result_path}：
{{
  "status": "BLOCKED",
  "stage": "{stage}",
  "phase": "",
  "artifact_dir": "{artifact_dir}",
  "handoff": "",
  "validation": "",
  "pending_questions": "",
  "summary": "缺少阶段 {stage} 的 skill 或 validator，无法继续。",
  "next_action": "实现该阶段 skill 后重试"
}}
"""

    validation_file = VALIDATION_BY_STAGE.get(stage, "")
    handoff_file = HANDOFF_BY_STAGE.get(stage, "")
    validation_policy = """
校验失败处理规则：
- 不要把 validation errors 机械改成通过。先判断错误类型。
- 如果错误是 invalid JSON、JSONDecodeError、Expecting delimiter、Invalid control character，按纯 JSON 序列化修复处理：读取 validator 输出中的 json_error 行列和短 context，重建内存 JSON 对象并用 serializer 重写 handoff，然后重新 json.load 和 validator。不要把它解释成 BOM/隐藏字符问题，不要在主流程展开读取完整 handoff 或 Markdown。
- 如果错误涉及 pending markers、待确认、open_questions、UNDECIDED、target_object_resolution.status=open、缺少用户决策、缺少产品/版本、缺少数据库类型、候选 API 选择等事实不足或人工确认问题，禁止自行替换字段，必须写 pending-questions.json 和 worker-result.json(status=NEED_USER_INPUT) 后停止。
- 只有纯文档结构、验收标准数量不足、字段遗漏但不需要新业务事实的问题，才允许 worker 基于已知需求自行补充并重新运行 validator。
- 如果不确定某个 validation error 是否需要用户确认，按 NEED_USER_INPUT 处理。
- 阶段边界不要询问“是否继续下一阶段”；阶段完成且 validator success=true 时直接写 worker-result.json(status=STAGE_COMPLETED)。是否进入下一阶段由 orchestrator 在主 session 中通过 pending-questions.json 统一确认。
"""
    stage_specific_notes = ""
    if stage == "requirement-analysis":
        stage_specific_notes = """
阶段特别注意：
- 必须先读取 workflow-input.json，并根据其中的 source_type/sources 选择 requirement-analysis 的输入模式。
- source_type=ticket_url 或 sources 中有 ticket_url 时，按 requirement-analysis 的 Mode A 执行。
- source_type=manual_text、document_file、goal_only 或只有自然语言需求时，按 requirement-analysis 的 Mode B 执行。
- WebFetch 或轻量抓取失败、跳转 SSO、403、超时或内容为空时，必须自动切换到 Playwright MCP 或浏览器抓取；不要把轻量抓取失败当作阶段失败。
- 先读取 ~/.claude/config/internal-urls.yaml；如果 sso_username、sso_password、sso_selectors 和 Playwright/MCP 能力可用，必须在 worker 内自动登录，不要把 SSO 回传主流程。
- 只有缺少 SSO 配置、MCP/浏览器不可用、自动登录失败、需要人机验证、缺少平台名称/版本、或存在关键澄清点时，才写 pending-questions.json。
- 进入产物阶段时必须先写 requirement-handoff.json，再运行/生成 requirement-validation.json，并尽早写 worker-result.json；Markdown 文档可以随后补齐。草稿也必须有 machine handoff。
"""
    elif stage == "design-phase":
        stage_specific_notes = """
阶段特别注意：
- 必须优先读取 requirement-handoff.json；不要依赖 workflow_goal 或聊天历史补事实。
- MCP 只检索平台上下文动作，不检索外部执行动作。
- 架构、中间件、实现方式分类、MCP 检索计划、候选 API 选择等确认点，在 worker 模式下都写 pending-questions.json。
- 选中基线 API 后必须调用详情并把接口路径、请求参数/契约、响应结果/契约写入 design-handoff.json；只写 API 名称或组件名不算可交接。
- 选中基线 API 后必须写入版本兼容证据：resolved_doc_version、contract_doc_version、version_match_policy、version_compatibility=PASS；contract_doc_version 不能高于 resolved_doc_version。
"""
    finalize_notes = make_finalize_recovery_notes(state, result_path)
    subagent_names = state.get("worker_subagents") or []
    if state.get("worker_subagents_enabled") and subagent_names:
        subagent_notes = f"""
worker 内部 subAgent 可选规则：
- 当前允许的 subAgent: {", ".join(subagent_names)}
- 只在高噪声、可独立的局部任务中使用 subAgent，例如资料检索、候选 API 查找、风险审查。
- subAgent 不负责写阶段产物，不负责更新 workflow-state，不负责询问用户。
- subAgent 返回的内容必须由当前 worker 汇总、判断，再写入正式文档、handoff、validation 或 pending-questions.json。
- 如果需要用户确认，仍由当前 worker 写 pending-questions.json 和 worker-result.json(status=NEED_USER_INPUT)，不要让 subAgent 直接提问。
"""
    else:
        subagent_notes = """
worker 内部 subAgent 当前未启用。请在当前 worker session 内直接完成阶段任务。
"""

    return f"""worker_mode: true
stage: {stage}
artifact_dir: {artifact_dir}
project_root: {project_root}
workflow_goal: {workflow_goal}

必须使用这个 Claude Code skill：
{stage_skill}

严格执行顺序：
1. 第一件事必须读取并理解上面的 SKILL.md 文件。不要只根据本 prompt 猜流程。
2. 子 skill 的流程规则优先级高于本 orchestrator prompt；本 prompt 只覆盖“交互方式”和“worker-result 写法”。
3. worker_mode 只把 AskQuestion 替换为 pending-questions.json，不改变子 skill 的抓取、分析、MCP、校验等规则。
4. 如果无法读取子 skill，立即写 {result_path}，status=BLOCKED，summary 写明“子 skill 未加载”，然后停止。
5. 这不是聊天问候任务。不要只回复“你好”“我可以帮你”等普通对话。必须实际执行阶段任务、读写文件，并最终写 worker-result.json。
6. 标准输出可以很短，但文件产物是必需的；没有 worker-result.json 就视为本次 worker 失败。

必须读取的运行文件：
- workflow-state: {state_path}
- workflow_input: {workflow_input}
- decisions_log: {decisions_log}
- prior_handoff: {prior_handoff or "(requirement-analysis 首次执行可没有 prior_handoff)"}

{stage_specific_notes}

{finalize_notes}

{subagent_notes}

交互规则：
- 不要直接向用户提问，不要调用 AskQuestion。
- 如果需要人工确认，先写 worker-checkpoint.json，再写 {pending_path}，立刻写 {result_path}，status=NEED_USER_INPUT，然后停止；禁止只写 pending-questions.json 而不写 worker-result.json。
- 如果你已经写出了 pending-questions.json，但发现剩余工作还很多、上下文变长、或不能确信能在本次 worker 内完成，必须立即写 worker-result.json(status=NEED_USER_INPUT) 并退出，让 orchestrator 处理决策和续跑。
- 如果 decisions_log 已经回答了当前确认点，使用该决策继续执行，并把证据写入阶段文档。
- 如果遇到无法在 worker 内自动完成的 SSO、人机验证、文件选择、外部系统操作、长时间人工处理或任何 worker 不能保留的有状态资源，不能依赖当前 worker 的浏览器、MCP 连接、临时进程或内存状态等待用户。写 worker-checkpoint.json、external-action.json 和 pending-questions.json，要求主流程完成外部动作并写 external-result.json；等 decisions_log 记录对应 resume_decision_id 后，读取 worker-checkpoint.json 和 external-result.json 断点继续。
- worker 每次启动时都必须先检查 worker-checkpoint.json、external-result.json 和 decisions_log。如果存在已完成的外部动作或用户决策，必须从 checkpoint 恢复，不要从头重复已完成步骤。

产物规则：
- 阶段产物必须写在 artifact_dir 或阶段 skill 指定的 requirements 产品目录下。
- 如果 requirement-analysis 识别出了产品目录，worker-result.json.artifact_dir 必须指向最终产品目录。
- 阶段完成后必须生成 {handoff_file} 和 {validation_file}。
- 所有 JSON 文件都必须用 JSON serializer 写入，禁止手工拼接 JSON 文本。推荐用 Python `json.dump(data, ensure_ascii=False, indent=2)` 或等价结构化写入；写完必须立即用 `json.load(open(path, encoding="utf-8"))` 重新读取校验。字符串里出现双引号、反斜杠、换行、中文标点时，让 serializer 自动转义，不要手动写未转义的 `"..."`。
- 如果发现 `*-handoff.json`、`pending-questions.json` 或 `worker-result.json` 解析失败，先用 serializer 重写并重跑 validator；不要把无效 JSON 当作阶段完成，也不要把排查方向转到 BOM/隐藏字符。
- 阶段完成后必须运行对应 validator；validation success=false 时按下面的校验失败处理规则分流，不允许把待确认事实伪造成已确认。

{validation_policy}

最后必须写 worker-result JSON 到：
{result_path}

worker-result.json 格式：
{{
  "status": "STAGE_COMPLETED|NEED_USER_INPUT|VALIDATION_FAILED|BLOCKED",
  "stage": "{stage}",
  "phase": "",
  "artifact_dir": "",
  "handoff": "",
  "validation": "",
  "pending_questions": "",
  "summary": "",
  "next_action": ""
}}
"""


def command_init(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(args.project_root)
    initial_input = build_initial_input(args)
    confirmation_policy = confirmation_policy_from_args(args)
    explicit_artifact = bool(args.artifact_dir or args.run_id)
    if not explicit_artifact and not args.no_reuse_existing:
        reusable_state = find_reusable_workflow(project_root, initial_input, args.stage)
        if reusable_state:
            reusable = load_state(reusable_state)
            artifact_dir = Path(reusable.get("artifact_dir") or reusable_state.parent).resolve()
            if confirmation_args_explicit(args):
                apply_confirmation_policy(reusable, confirmation_policy, full_auto=bool(args.full_auto), auto_confirm=bool(args.auto_confirm))
            write_last_state_pointer(project_root, reusable_state, artifact_dir)
            add_history(reusable, "init_reused_existing", {
                "stage": args.stage,
                "input_source_type": initial_input.get("source_type", ""),
                "confirmation_policy": reusable.get("stage_confirmation_policy", "default"),
            })
            save_state(reusable_state, reusable)
            print(json.dumps({
                "state": str(reusable_state),
                "artifact_dir": str(artifact_dir),
                "reused_existing": True,
                "message": "matching active workflow already exists; reused it instead of creating a duplicate",
            }, ensure_ascii=False, indent=2))
            return 0

    run_id = args.run_id or _dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    artifact_dir = Path(args.artifact_dir).resolve() if args.artifact_dir else default_artifact_dir(project_root, run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    workflow_goal = args.goal or initial_input.get("goal") or default_goal_for_sources(initial_input.get("sources", []), initial_input.get("source_type", ""))

    state = {
        "schema_version": "1.0",
        "workflow_goal": workflow_goal,
        "workflow_input": "workflow-input.json",
        "input_source_type": initial_input["source_type"],
        "input_sources_count": len(initial_input.get("sources", [])),
        "run_id": run_id,
        "project_root": str(project_root),
        "artifact_dir": str(artifact_dir),
        "current_stage": args.stage,
        "current_phase": "",
        "stage_status": "READY",
        "latest_handoff": "",
        "latest_validation": "",
        "pending_questions": "",
        "pending_next_stage": "",
        "completed_stage_waiting_approval": "",
        "decisions_log": "decisions.jsonl",
        "retry_count": 0,
        "max_retries": args.max_retries,
        "max_missing_result_recoveries": args.max_missing_result_recoveries,
        "missing_result_recovery_count": 0,
        "missing_result_recovery_repeat_count": 0,
        "auto_advance_stages": bool(args.auto_advance),
        "auto_decision_rounds": args.auto_decision_rounds,
        "max_auto_decisions": args.max_auto_decisions,
        "auto_decision_count": 0,
        "worker_subagents_enabled": bool(args.enable_worker_subagents),
        "worker_subagents": stage_subagent_names(args.stage) if args.enable_worker_subagents else [],
        "history": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    apply_confirmation_policy(state, confirmation_policy, full_auto=bool(args.full_auto), auto_confirm=bool(args.auto_confirm))
    write_json(artifact_dir / "workflow-input.json", initial_input)
    add_history(state, "initialized", {"stage": args.stage, "input_source_type": initial_input["source_type"]})
    state_path = state_path_from_artifact(artifact_dir)
    write_json(state_path, state)
    write_last_state_pointer(project_root, state_path, artifact_dir)
    (artifact_dir / "decisions.jsonl").touch(exist_ok=True)
    print(json.dumps({"state": str(state_path), "artifact_dir": str(artifact_dir), "reused_existing": False}, ensure_ascii=False, indent=2))
    return 0


def command_prompt(args: argparse.Namespace) -> int:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    artifact_dir = Path(state["artifact_dir"])
    prompt = make_worker_prompt(state)
    prompt_path = artifact_dir / "worker-prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    add_history(state, "worker_prompt_generated", {"path": str(prompt_path), "stage": state["current_stage"]})
    save_state(state_path, state)
    print(str(prompt_path))
    return 0


def add_decision_to_state(
    state_path: Path,
    *,
    question_batch_id: str,
    question_id: str,
    selected: str,
    free_text: str = "",
    decision_id: str | None = None,
    decided_by: str = "user",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state_path = state_path.resolve()
    state = load_state(state_path)
    artifact_dir = Path(state["artifact_dir"])
    decision = {
        "decision_id": decision_id or f"D-{_dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "question_batch_id": question_batch_id,
        "question_id": question_id,
        "selected": selected,
        "free_text": free_text or "",
        "decided_by": decided_by,
        "decided_at": now_iso(),
    }
    if metadata:
        decision.update(metadata)
    append_jsonl(artifact_dir / state.get("decisions_log", "decisions.jsonl"), decision)
    pending_next_stage = state.get("pending_next_stage") or ""
    completed_stage = state.get("completed_stage_waiting_approval") or state.get("current_stage", "")
    if pending_next_stage and question_id == f"workflow.advance_to.{pending_next_stage}":
        selected_normalized = (selected or "").lower()
        if selected_normalized in {"approve", "continue", "yes", "y"}:
            state["current_stage"] = pending_next_stage
            state["current_phase"] = ""
            state["stage_status"] = "READY"
            state["retry_count"] = 0
            add_history(state, "stage_boundary_approved", {"from": completed_stage, "to": pending_next_stage})
        elif selected_normalized in {"revise", "rework", "modify", "no", "n"}:
            state["current_stage"] = completed_stage
            state["current_phase"] = ""
            state["stage_status"] = "READY"
            state["retry_count"] = 0
            add_history(state, "stage_boundary_revision_requested", {"stage": completed_stage, "next_stage": pending_next_stage})
        else:
            state["stage_status"] = "BLOCKED"
            add_history(state, "stage_boundary_stopped", {"stage": completed_stage, "next_stage": pending_next_stage, "selected": selected})
        state["pending_next_stage"] = ""
        state["completed_stage_waiting_approval"] = ""
    else:
        state["stage_status"] = "READY"
    state["pending_questions"] = ""
    add_history(state, "decision_added", decision)
    save_state(state_path, state)
    return {
        "decision": decision,
        "state": str(state_path),
        "stage_status": state["stage_status"],
        "current_stage": state["current_stage"],
        "resume_worker_required": state["stage_status"] == "READY",
        "next_internal_action": "call run-loop; do not execute the stage inside the main session",
    }


def command_add_decision(args: argparse.Namespace) -> int:
    summary = add_decision_to_state(
        Path(args.state),
        question_batch_id=args.question_batch_id,
        question_id=args.question_id,
        selected=args.selected,
        free_text=args.free_text or "",
        decision_id=args.decision_id,
        decided_by="user",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def pending_external_action_blocker(state: dict[str, Any]) -> dict[str, Any] | None:
    artifact_dir = Path(state["artifact_dir"])
    action_path = artifact_dir / "external-action.json"
    if not action_path.exists():
        return None
    action = read_json(action_path, {})
    if not isinstance(action, dict):
        return {"path": str(action_path), "reason": "external-action.json is invalid"}
    action_type = str(action.get("action_type") or "")
    action_id = str(action.get("action_id") or "")
    result = read_json(artifact_dir / "external-result.json", {})
    result_completed = (
        isinstance(result, dict)
        and result.get("action_id") == action_id
        and result.get("status") == "COMPLETED"
    )
    if action.get("status") == "NEED_MAIN_ACTION" and not result_completed:
        if action_type in EXTERNAL_ACTION_REQUIRES_MAIN_SESSION or action_type:
            return {
                "path": str(action_path),
                "action_id": action_id,
                "action_type": action_type,
                "reason": "external action requires main session or real user/environment state",
            }
    return None


def recommended_or_default_decision(question: dict[str, Any]) -> dict[str, Any] | None:
    question_id = question.get("id")
    if not question_id:
        return None
    default = question.get("default_if_full_auto")
    if isinstance(default, str) and default.strip():
        return {
            "question_id": question_id,
            "selected": default.strip(),
            "free_text": "",
            "confidence": 0.55,
            "rationale": "Used default_if_full_auto because AI structured decision was unavailable.",
            "source": "default_if_full_auto",
        }
    options = question.get("options") if isinstance(question.get("options"), list) else []
    for option in options:
        if isinstance(option, dict) and option.get("recommended") and option.get("key"):
            return {
                "question_id": question_id,
                "selected": str(option["key"]),
                "free_text": "",
                "confidence": 0.5,
                "rationale": "Used the recommended option because AI structured decision was unavailable.",
                "source": "recommended_option",
            }
    if len(options) == 1 and isinstance(options[0], dict) and options[0].get("key"):
        return {
            "question_id": question_id,
            "selected": str(options[0]["key"]),
            "free_text": "",
            "confidence": 0.45,
            "rationale": "Only one option was available.",
            "source": "single_option",
        }
    return None


def fallback_auto_decisions(pending: dict[str, Any]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for question in pending.get("questions", []):
        if isinstance(question, dict):
            decision = recommended_or_default_decision(question)
            if decision:
                decisions.append(decision)
    return decisions


def extract_cli_text_result(stdout: str) -> str:
    parsed = parse_cli_json_output(stdout)
    result = parsed.get("result")
    candidates: list[Any] = [result]
    if isinstance(result, dict):
        candidates.extend(result.get(key) for key in ["result", "text", "content", "message", "completion"])
    for item in candidates:
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, list):
            chunks: list[str] = []
            for part in item:
                if isinstance(part, str):
                    chunks.append(part)
                elif isinstance(part, dict):
                    text = part.get("text") or part.get("content")
                    if isinstance(text, str):
                        chunks.append(text)
            if chunks:
                return "\n".join(chunks).strip()
    return (stdout or "").strip()


def parse_auto_decision_json(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    candidates = [stripped]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        candidates.append(stripped[start:end + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def make_auto_decision_prompt(
    state: dict[str, Any],
    pending: dict[str, Any],
    *,
    rounds: int,
    max_decisions: int,
) -> str:
    artifact_dir = Path(state["artifact_dir"])
    return f"""你是 workflow-orchestrator 的全自动确认 worker。你的任务是代替用户回答 pending-questions.json，但只能做可审计、保守、可回滚的决策。

请进行 {rounds} 轮复核后再给最终答案：
1. 事实复核：列出已知事实、问题、可选项、默认项。
2. 风险复核：寻找会改变范围、数据来源、权限、安全、外部系统、不可逆动作的风险。
3. 最终决策：如果证据足够，选择选项；如果不够或涉及真实外部动作，返回 NEED_USER_INPUT。

不要输出隐藏推理链，只输出简短 review_rounds 摘要和最终 JSON。

硬规则：
- 不要编造用户明确事实。
- 优先选择 pending question 中的 default_if_full_auto；没有 default 时优先选择 recommended=true 的选项，但必须检查风险。
- 对 workflow.advance_to.* 阶段边界，如果上一阶段 validation 已成功且没有 open risk，通常选择 approve。
- 若问题涉及 SSO、人机验证、文件选择、外部系统操作、付款、删除、生产变更、法律/合规承诺，返回 NEED_USER_INPUT。
- 若选项不足以表达答案，使用 free_text，但 selected 仍应填一个稳定值；实在无法决定则返回 NEED_USER_INPUT。
- 本批最多回答 {max_decisions} 个问题。

当前轻量状态：
{json.dumps({
    "workflow_goal": state.get("workflow_goal"),
    "current_stage": state.get("current_stage"),
    "current_phase": state.get("current_phase"),
    "latest_handoff": state.get("latest_handoff"),
    "latest_validation": state.get("latest_validation"),
    "pending_next_stage": state.get("pending_next_stage"),
    "completed_stage_waiting_approval": state.get("completed_stage_waiting_approval"),
    "artifact_dir": str(artifact_dir),
}, ensure_ascii=False, indent=2)}

pending-questions.json:
{json.dumps(pending, ensure_ascii=False, indent=2)}

只输出 JSON，格式如下：
{{
  "status": "AUTO_DECIDED|NEED_USER_INPUT",
  "reason": "",
  "review_rounds": [
    {{"round": 1, "summary": ""}},
    {{"round": 2, "summary": ""}},
    {{"round": 3, "summary": ""}}
  ],
  "decisions": [
    {{
      "question_id": "",
      "selected": "",
      "free_text": "",
      "confidence": 0.0,
      "rationale": ""
    }}
  ]
}}
"""


def run_auto_decision_worker(
    state_path: Path,
    *,
    rounds: int,
    max_decisions: int,
    output_format: str,
    max_turns: int,
    permission_mode: str | None,
    allowed_tools: str | None,
) -> dict[str, Any]:
    state_path = state_path.resolve()
    state = load_state(state_path)
    artifact_dir = Path(state["artifact_dir"])
    pending_path = artifact_dir / "pending-questions.json"
    pending = read_json(pending_path, {})
    if not isinstance(pending, dict) or not pending.get("questions"):
        return {"resolved": False, "reason": "pending-questions.json missing or empty", "pending": str(pending_path)}

    blocker = pending_external_action_blocker(state)
    if blocker:
        add_history(state, "auto_decision_blocked_by_external_action", blocker)
        save_state(state_path, state)
        return {"resolved": False, "reason": "external_action_requires_main_session", "blocker": blocker}

    current_count = int(state.get("auto_decision_count", 0))
    configured_limit = int(state.get("max_auto_decisions", max_decisions))
    remaining = max(0, min(max_decisions, configured_limit - current_count))
    if remaining <= 0:
        add_history(state, "auto_decision_limit_reached", {"max_auto_decisions": configured_limit})
        save_state(state_path, state)
        return {"resolved": False, "reason": "max_auto_decisions reached", "max_auto_decisions": configured_limit}

    prompt = make_auto_decision_prompt(state, pending, rounds=rounds, max_decisions=remaining)
    prompt_path = artifact_dir / "auto-decision-prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    decisions: list[dict[str, Any]] = []
    review_rounds: list[Any] = []
    reason = ""
    raw_status = "NEED_USER_INPUT"
    claude = shutil.which("claude")
    completed: subprocess.CompletedProcess[str] | None = None
    log_path = artifact_dir / "auto-decision-cli-output.log"
    if claude:
        cmd = [
            claude,
            "-p",
            "--input-format",
            "text",
            "--output-format",
            output_format,
            "--max-turns",
            str(max_turns),
            "--no-session-persistence",
            "--permission-mode",
            permission_mode or "default",
            "--add-dir",
            str(Path(state["project_root"]).resolve()),
            "--add-dir",
            str(artifact_dir.resolve()),
        ]
        tool_args = allowed_tools or DEFAULT_AUTO_DECISION_ALLOWED_TOOLS
        if tool_args:
            cmd.append("--allowed-tools")
            cmd.append(tool_args)
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")
        completed = subprocess.run(
            cmd,
            cwd=state["project_root"],
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        log_path.write_text((completed.stdout or "") + ("\nSTDERR:\n" + completed.stderr if completed.stderr else ""), encoding="utf-8")
        decision_text = extract_cli_text_result(completed.stdout or "")
        decision_data = parse_auto_decision_json(decision_text)
        if isinstance(decision_data, dict):
            raw_status = str(decision_data.get("status") or "")
            reason = str(decision_data.get("reason") or "")
            review_rounds = decision_data.get("review_rounds") if isinstance(decision_data.get("review_rounds"), list) else []
            raw_decisions = decision_data.get("decisions") if isinstance(decision_data.get("decisions"), list) else []
            for item in raw_decisions[:remaining]:
                if isinstance(item, dict) and item.get("question_id") and item.get("selected"):
                    decisions.append(item)

    if not decisions:
        fallback = fallback_auto_decisions(pending)[:remaining]
        if fallback:
            decisions = fallback
            raw_status = "AUTO_DECIDED"
            reason = reason or "AI decision unavailable or empty; used explicit full-auto defaults/recommended options."

    if raw_status != "AUTO_DECIDED" or not decisions:
        add_history(state, "auto_decision_needs_user", {
            "reason": reason or "AI auto decision declined or no safe default was available",
            "prompt": str(prompt_path),
            "log": str(log_path) if log_path.exists() else "",
        })
        save_state(state_path, state)
        return {
            "resolved": False,
            "reason": reason or "AI auto decision declined or no safe default was available",
            "prompt": str(prompt_path),
            "log": str(log_path) if log_path.exists() else "",
            "returncode": completed.returncode if completed else None,
        }

    question_batch_id = str(pending.get("question_batch_id") or f"AUTO-{_dt.datetime.now().strftime('%Y%m%d%H%M%S')}")
    applied: list[dict[str, Any]] = []
    for decision in decisions[:remaining]:
        summary = add_decision_to_state(
            state_path,
            question_batch_id=question_batch_id,
            question_id=str(decision.get("question_id")),
            selected=str(decision.get("selected")),
            free_text=str(decision.get("free_text") or ""),
            decided_by="ai-auto",
            metadata={
                "confidence": decision.get("confidence"),
                "rationale": decision.get("rationale") or decision.get("reason") or "",
                "auto_decision_rounds": rounds,
            },
        )
        applied.append(summary["decision"])

    state = load_state(state_path)
    state["auto_decision_count"] = int(state.get("auto_decision_count", 0)) + len(applied)
    add_history(state, "auto_decision_applied", {
        "count": len(applied),
        "rounds": rounds,
        "reason": reason,
        "prompt": str(prompt_path),
        "log": str(log_path) if log_path.exists() else "",
    })
    save_state(state_path, state)
    append_jsonl_all(artifact_dir / "auto-decisions.jsonl", [
        {
            "at": now_iso(),
            "question_batch_id": question_batch_id,
            "decision": decision,
            "review_rounds": review_rounds,
            "reason": reason,
            "prompt": str(prompt_path),
            "log": str(log_path) if log_path.exists() else "",
            "returncode": completed.returncode if completed else None,
        }
        for decision in applied
    ])
    return {
        "resolved": True,
        "applied_count": len(applied),
        "decisions": applied,
        "review_rounds": review_rounds,
        "reason": reason,
        "prompt": str(prompt_path),
        "log": str(log_path) if log_path.exists() else "",
        "returncode": completed.returncode if completed else None,
    }


def validation_success(validation_path: Path) -> bool | None:
    data = read_json(validation_path)
    if not isinstance(data, dict):
        return None
    return bool(data.get("success"))


def next_stage(stage: str) -> str | None:
    try:
        index = STAGES.index(stage)
    except ValueError:
        return None
    if index + 1 >= len(STAGES):
        return None
    return STAGES[index + 1]


def record_worker_result(state_path: Path, result_path: Path) -> dict[str, Any]:
    state_path = state_path.resolve()
    state = load_state(state_path)
    result_path = result_path.resolve()
    result = read_json(result_path)
    if not isinstance(result, dict):
        raise SystemExit(f"worker result not found or invalid: {result_path}")

    status = result.get("status")
    artifact_dir = Path(result.get("artifact_dir") or state["artifact_dir"]).resolve()
    if artifact_dir != Path(state["artifact_dir"]).resolve():
        old_state_path = state_path
        old_artifact_dir = Path(state["artifact_dir"]).resolve()
        state["artifact_dir"] = str(artifact_dir)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        for filename in [
            state.get("decisions_log", "decisions.jsonl"),
            "worker-result.json",
            "worker-run-metrics.json",
            "worker-cli-output.log",
            "worker-prompt.md",
            "workflow-input.json",
            "pending-questions.json",
            "worker-checkpoint.json",
            "external-action.json",
            "external-result.json",
        ]:
            copy_if_exists(old_artifact_dir / filename, artifact_dir / filename)
        copied_metrics_path = artifact_dir / "worker-run-metrics.json"
        copied_metrics = read_json(copied_metrics_path, {})
        if isinstance(copied_metrics, dict):
            for key, filename in {
                "log_path": "worker-cli-output.log",
                "prompt_path": "worker-prompt.md",
            }.items():
                copied_path = artifact_dir / filename
                if copied_path.exists():
                    copied_metrics[key] = str(copied_path)
            write_json(copied_metrics_path, copied_metrics)
        state_path = artifact_dir / "workflow-state.json"
        if not state_path.exists():
            write_json(state_path, state)
        add_history(state, "artifact_dir_changed", {"from": str(old_state_path.parent), "to": str(artifact_dir)})

    state["current_phase"] = result.get("phase") or state.get("current_phase", "")
    state["latest_handoff"] = result.get("handoff") or state.get("latest_handoff", "")
    state["latest_validation"] = result.get("validation") or state.get("latest_validation", "")
    state["pending_questions"] = result.get("pending_questions") or ""

    if status == "NEED_USER_INPUT":
        state["stage_status"] = "NEED_USER_INPUT"
    elif status == "VALIDATION_FAILED":
        state["stage_status"] = "VALIDATION_FAILED"
        state["retry_count"] = int(state.get("retry_count", 0)) + 1
    elif status == "BLOCKED":
        state["stage_status"] = "BLOCKED"
    elif status == "STAGE_COMPLETED":
        state.pop("recovery_finalize", None)
        validation_path = Path(state["latest_validation"]) if state.get("latest_validation") else artifact_dir / VALIDATION_BY_STAGE.get(state["current_stage"], "")
        if validation_path and not validation_path.is_absolute():
            validation_path = artifact_dir / validation_path
        ok = validation_success(validation_path) if validation_path else None
        if ok is not True:
            state["stage_status"] = "VALIDATION_FAILED"
            state["retry_count"] = int(state.get("retry_count", 0)) + 1
            add_history(state, "validation_not_successful", {"validation": str(validation_path), "success": ok})
        else:
            following = next_stage(state["current_stage"])
            if following:
                if state.get("auto_advance_stages"):
                    state["current_stage"] = following
                    state["current_phase"] = ""
                    state["stage_status"] = "READY"
                    state["retry_count"] = 0
                    add_history(state, "stage_auto_advanced", {"to": following})
                else:
                    pending_path = write_stage_boundary_questions(
                        artifact_dir,
                        completed_stage=state["current_stage"],
                        next_stage_name=following,
                        handoff=state.get("latest_handoff", ""),
                        validation=state.get("latest_validation", ""),
                    )
                    state["current_phase"] = "stage-boundary"
                    state["stage_status"] = "NEED_USER_INPUT"
                    state["pending_questions"] = str(pending_path)
                    state["pending_next_stage"] = following
                    state["completed_stage_waiting_approval"] = state["current_stage"]
                    state["retry_count"] = 0
                    add_history(state, "stage_boundary_confirmation_required", {"from": state["current_stage"], "to": following, "pending": str(pending_path)})
            else:
                state["stage_status"] = "COMPLETED"
    else:
        raise SystemExit(f"unknown worker status: {status}")

    add_history(state, "worker_result_recorded", {"result": str(result_path), "status": status})
    save_state(state_path, state)
    return {"state": str(state_path), "stage_status": state["stage_status"], "current_stage": state["current_stage"]}


def pending_questions_answered(pending: dict[str, Any], decisions: list[dict[str, Any]]) -> bool:
    batch_id = pending.get("question_batch_id")
    questions = pending.get("questions") if isinstance(pending.get("questions"), list) else []
    question_ids = {
        str(question.get("id"))
        for question in questions
        if isinstance(question, dict) and question.get("id")
    }
    if not question_ids:
        return False
    answered = {
        str(decision.get("question_id"))
        for decision in decisions
        if decision.get("question_id")
        and (not batch_id or decision.get("question_batch_id") == batch_id)
    }
    return question_ids.issubset(answered)


def recovery_signature(pending: dict[str, Any] | None, checkpoint: dict[str, Any] | None) -> str:
    if isinstance(pending, dict) and pending.get("question_batch_id"):
        return f"pending:{pending.get('question_batch_id')}"
    if isinstance(checkpoint, dict) and checkpoint.get("checkpoint_id"):
        return f"checkpoint:{checkpoint.get('checkpoint_id')}"
    if isinstance(checkpoint, dict) and checkpoint.get("resume_from"):
        return f"checkpoint:{checkpoint.get('stage', '')}:{checkpoint.get('phase', '')}:{checkpoint.get('resume_from')}"
    return "missing-result:no-contract-files"


def increment_recovery_guard(state: dict[str, Any], signature: str) -> tuple[bool, int]:
    max_recoveries = int(state.get("max_missing_result_recoveries", DEFAULT_MAX_MISSING_RESULT_RECOVERIES))
    previous = state.get("last_missing_result_recovery_signature")
    count = int(state.get("missing_result_recovery_repeat_count", 0))
    count = count + 1 if previous == signature else 1
    state["last_missing_result_recovery_signature"] = signature
    state["missing_result_recovery_repeat_count"] = count
    state["missing_result_recovery_count"] = int(state.get("missing_result_recovery_count", 0)) + 1
    return count <= max_recoveries, count


def recover_missing_worker_result(state_path: Path, run_summary: dict[str, Any]) -> dict[str, Any]:
    state_path = state_path.resolve()
    state = load_state(state_path)
    artifact_dir = Path(state["artifact_dir"])
    pending_path = artifact_dir / "pending-questions.json"
    checkpoint_path = artifact_dir / "worker-checkpoint.json"
    result_path = artifact_dir / "worker-result.json"
    pending = read_json(pending_path, {})
    checkpoint = read_json(checkpoint_path, {})
    pending = pending if isinstance(pending, dict) else {}
    checkpoint = checkpoint if isinstance(checkpoint, dict) else {}
    finalize_candidate = find_partial_finalize_candidate(state) if not pending and not checkpoint else None
    signature = partial_finalize_signature(finalize_candidate) if finalize_candidate else recovery_signature(pending, checkpoint)
    allowed, repeat_count = increment_recovery_guard(state, signature)
    if not allowed:
        state["stage_status"] = "BLOCKED"
        add_history(state, "missing_worker_result_recovery_limit_reached", {
            "signature": signature,
            "repeat_count": repeat_count,
            "run": run_summary,
        })
        save_state(state_path, state)
        return {
            "recovered": False,
            "state": str(state_path),
            "stage_status": "BLOCKED",
            "reason": "missing worker-result recovery limit reached",
            "signature": signature,
            "repeat_count": repeat_count,
        }

    decisions = read_jsonl(artifact_dir / state.get("decisions_log", "decisions.jsonl"))
    if pending.get("status") == "NEED_USER_INPUT" and pending.get("questions"):
        answered = pending_questions_answered(pending, decisions)
        if answered and checkpoint:
            state["stage_status"] = "READY"
            state["current_phase"] = str(checkpoint.get("phase") or state.get("current_phase", ""))
            state["pending_questions"] = ""
            reason = "pending questions already answered; resume from checkpoint"
        else:
            state["stage_status"] = "NEED_USER_INPUT"
            state["current_phase"] = str(pending.get("phase") or state.get("current_phase", ""))
            state["pending_questions"] = str(pending_path)
            reason = "pending questions found without worker-result; recovered to NEED_USER_INPUT"
        synthetic = {
            "status": "NEED_USER_INPUT" if state["stage_status"] == "NEED_USER_INPUT" else "RECOVERED_READY",
            "stage": state.get("current_stage", ""),
            "phase": state.get("current_phase", ""),
            "artifact_dir": str(artifact_dir),
            "handoff": state.get("latest_handoff", ""),
            "validation": state.get("latest_validation", ""),
            "pending_questions": str(pending_path),
            "summary": reason,
            "next_action": "handle pending questions" if state["stage_status"] == "NEED_USER_INPUT" else "run-loop resumes worker from checkpoint",
        }
        write_json(result_path, synthetic)
        add_history(state, "missing_worker_result_recovered", {
            "reason": reason,
            "signature": signature,
            "repeat_count": repeat_count,
            "pending": str(pending_path),
            "checkpoint": str(checkpoint_path) if checkpoint else "",
            "run": run_summary,
        })
        save_state(state_path, state)
        return {
            "recovered": True,
            "state": str(state_path),
            "stage_status": state["stage_status"],
            "reason": reason,
            "pending_questions": str(pending_path),
            "checkpoint": str(checkpoint_path) if checkpoint else "",
            "synthetic_worker_result": str(result_path),
        }

    if checkpoint:
        state["stage_status"] = "READY"
        state["current_phase"] = str(checkpoint.get("phase") or state.get("current_phase", ""))
        state["pending_questions"] = ""
        state.pop("recovery_finalize", None)
        reason = "checkpoint found without worker-result; recovered to READY"
        write_json(result_path, {
            "status": "RECOVERED_READY",
            "stage": state.get("current_stage", ""),
            "phase": state.get("current_phase", ""),
            "artifact_dir": str(artifact_dir),
            "handoff": state.get("latest_handoff", ""),
            "validation": state.get("latest_validation", ""),
            "pending_questions": "",
            "summary": reason,
            "next_action": "run-loop resumes worker from checkpoint",
        })
        add_history(state, "missing_worker_result_recovered", {
            "reason": reason,
            "signature": signature,
            "repeat_count": repeat_count,
            "checkpoint": str(checkpoint_path),
            "run": run_summary,
        })
        save_state(state_path, state)
        return {
            "recovered": True,
            "state": str(state_path),
            "stage_status": "READY",
            "reason": reason,
            "checkpoint": str(checkpoint_path),
            "synthetic_worker_result": str(result_path),
        }

    if finalize_candidate:
        state["stage_status"] = "READY"
        state["current_phase"] = "finalize-recovery"
        state["pending_questions"] = ""
        state["recovery_finalize"] = finalize_candidate
        handoff_path = Path(str(finalize_candidate.get("handoff", "")))
        validation_path = Path(str(finalize_candidate.get("validation", "")))
        if handoff_path.exists():
            state["latest_handoff"] = str(handoff_path)
        if validation_path.exists():
            state["latest_validation"] = str(validation_path)
        reason = "partial stage artifacts found; recovered to READY for finalize-only worker"
        write_json(result_path, {
            "status": "RECOVERED_READY",
            "stage": state.get("current_stage", ""),
            "phase": "finalize-recovery",
            "artifact_dir": str(artifact_dir),
            "handoff": state.get("latest_handoff", ""),
            "validation": state.get("latest_validation", ""),
            "pending_questions": "",
            "summary": reason,
            "next_action": "run-loop starts a finalize-only worker; do not complete the stage in the main session",
        })
        add_history(state, "missing_worker_result_recovered", {
            "reason": reason,
            "signature": signature,
            "repeat_count": repeat_count,
            "finalize_candidate": finalize_candidate,
            "run": run_summary,
        })
        save_state(state_path, state)
        return {
            "recovered": True,
            "state": str(state_path),
            "stage_status": "READY",
            "reason": reason,
            "finalize_candidate": finalize_candidate,
            "synthetic_worker_result": str(result_path),
        }

    state["stage_status"] = "BLOCKED"
    add_history(state, "worker_result_missing", {"run": run_summary, "reason": "no pending questions or checkpoint for recovery"})
    save_state(state_path, state)
    return {
        "recovered": False,
        "state": str(state_path),
        "stage_status": "BLOCKED",
        "reason": "worker-result.json missing and no pending questions/checkpoint could be used for recovery",
    }


def command_record_result(args: argparse.Namespace) -> int:
    summary = record_worker_result(Path(args.state), Path(args.result))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def command_status(args: argparse.Namespace) -> int:
    state = load_state(resolve_state_path(args.state, args.artifact_dir))
    artifact_dir = Path(state.get("artifact_dir") or ".")
    metrics_path = artifact_dir / "worker-run-metrics.json"
    metrics = read_json(metrics_path, {}) if metrics_path.exists() else {}
    checkpoint_path = artifact_dir / "worker-checkpoint.json"
    external_action_path = artifact_dir / "external-action.json"
    external_result_path = artifact_dir / "external-result.json"
    auto_decisions_path = artifact_dir / "auto-decisions.jsonl"
    summary = {
        "workflow_goal": state.get("workflow_goal"),
        "workflow_input": str(initial_input_path(state)),
        "input_source_type": state.get("input_source_type", ""),
        "input_sources_count": state.get("input_sources_count", 0),
        "artifact_dir": state.get("artifact_dir"),
        "current_stage": state.get("current_stage"),
        "current_phase": state.get("current_phase"),
        "stage_status": state.get("stage_status"),
        "latest_handoff": state.get("latest_handoff"),
        "latest_validation": state.get("latest_validation"),
        "pending_questions": state.get("pending_questions"),
        "pending_next_stage": state.get("pending_next_stage", ""),
        "completed_stage_waiting_approval": state.get("completed_stage_waiting_approval", ""),
        "auto_advance_stages": state.get("auto_advance_stages", False),
        "full_auto": state.get("full_auto", False),
        "auto_confirm_mode": state.get("auto_confirm_mode", "manual"),
        "stage_confirmation_policy": state.get("stage_confirmation_policy", "default"),
        "manual_confirmation_stages": state.get("manual_confirmation_stages", DEFAULT_MANUAL_CONFIRMATION_STAGES),
        "ai_confirmation_stages": state.get("ai_confirmation_stages", [stage for stage in STAGES if stage not in DEFAULT_MANUAL_CONFIRMATION_STAGES]),
        "current_pending_confirmation_stage": pending_confirmation_stage(state),
        "current_pending_ai_confirmation_enabled": ai_confirmation_enabled_for_state(state),
        "auto_decision_rounds": state.get("auto_decision_rounds", 0),
        "max_auto_decisions": state.get("max_auto_decisions", 0),
        "auto_decision_count": state.get("auto_decision_count", 0),
        "worker_subagents_enabled": state.get("worker_subagents_enabled", False),
        "worker_subagents": state.get("worker_subagents", []),
        "checkpoint": str(checkpoint_path) if checkpoint_path.exists() else "",
        "external_action": str(external_action_path) if external_action_path.exists() else "",
        "external_result": str(external_result_path) if external_result_path.exists() else "",
        "auto_decisions": str(auto_decisions_path) if auto_decisions_path.exists() else "",
        "retry_count": state.get("retry_count"),
        "max_missing_result_recoveries": state.get("max_missing_result_recoveries", DEFAULT_MAX_MISSING_RESULT_RECOVERIES),
        "missing_result_recovery_count": state.get("missing_result_recovery_count", 0),
        "missing_result_recovery_repeat_count": state.get("missing_result_recovery_repeat_count", 0),
        "worker_proof": compact_worker_proof(metrics, metrics_path) if metrics else {
            "worker_used": False,
            "reason": "worker-run-metrics.json not found",
        },
        "latest_worker_metrics": {
            "path": str(metrics_path) if metrics else "",
            "returncode": metrics.get("returncode"),
            "duration_seconds": metrics.get("duration_seconds"),
            "session_id": metrics.get("session_id"),
            "num_turns": metrics.get("num_turns"),
            "total_cost_usd": metrics.get("total_cost_usd"),
            "usage": metrics.get("usage"),
        } if metrics else {},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def compact_worker_proof(metrics: dict[str, Any], metrics_path: Path | None = None) -> dict[str, Any]:
    command = metrics.get("command") if isinstance(metrics.get("command"), list) else []
    command_text = " ".join(str(part) for part in command)
    uses_print_worker = "-p" in command or "--print" in command
    resumes_session = any(part in {"--resume", "-r", "--continue", "-c"} for part in command)
    disables_session_persistence = "--no-session-persistence" in command
    worker_used = bool(metrics.get("is_worker")) and metrics.get("worker_invocation") == "claude -p" and uses_print_worker and not resumes_session
    return {
        "worker_used": worker_used,
        "worker_invocation": metrics.get("worker_invocation", ""),
        "session_isolation": metrics.get("session_isolation", ""),
        "started_at": metrics.get("started_at", ""),
        "ended_at": metrics.get("ended_at", ""),
        "duration_seconds": metrics.get("duration_seconds"),
        "returncode": metrics.get("returncode"),
        "session_id": metrics.get("session_id"),
        "stdout_classification": metrics.get("stdout_classification"),
        "worker_subagents_enabled": metrics.get("worker_subagents_enabled", False),
        "allowed_subagents": metrics.get("allowed_subagents", []),
        "metrics_path": str(metrics_path) if metrics_path else "",
        "log_path": metrics.get("log_path", ""),
        "prompt_path": metrics.get("prompt_path", ""),
        "command_contains_claude_print": uses_print_worker,
        "command_resumes_existing_session": resumes_session,
        "command_disables_session_persistence": disables_session_persistence,
        "command": command_text,
    }


def audit_worker_isolation(state_path: Path) -> dict[str, Any]:
    state_path = state_path.resolve()
    state = load_state(state_path)
    artifact_dir = Path(state["artifact_dir"])
    metrics_path = artifact_dir / "worker-run-metrics.json"
    result_path = artifact_dir / "worker-result.json"
    pending_path = artifact_dir / "pending-questions.json"
    metrics = read_json(metrics_path, {})
    result = read_json(result_path, {})
    proof = compact_worker_proof(metrics, metrics_path) if isinstance(metrics, dict) and metrics else {
        "worker_used": False,
        "reason": "worker-run-metrics.json not found",
        "metrics_path": str(metrics_path),
    }
    issues: list[str] = []
    if not proof.get("worker_used"):
        issues.append("No auditable isolated claude -p worker run was found for the latest stage.")
    if not result_path.exists():
        issues.append("worker-result.json is missing; the latest worker did not complete the file contract.")
    if proof.get("stdout_classification") == "likely_greeting_only":
        issues.append("Worker stdout looks like a greeting-only response; it may not have executed the stage.")
    if proof.get("command_resumes_existing_session"):
        issues.append("Worker command used resume/continue; this breaks session isolation.")

    return {
        "state": str(state_path),
        "artifact_dir": str(artifact_dir),
        "current_stage": state.get("current_stage"),
        "stage_status": state.get("stage_status"),
        "worker_isolation_ok": bool(proof.get("worker_used")) and result_path.exists() and not issues,
        "worker_proof": proof,
        "worker_result": {
            "path": str(result_path),
            "exists": result_path.exists(),
            "status": result.get("status") if isinstance(result, dict) else None,
            "summary": result.get("summary") if isinstance(result, dict) else "",
            "pending_questions": result.get("pending_questions") if isinstance(result, dict) else "",
        },
        "pending_questions": {
            "path": str(pending_path),
            "exists": pending_path.exists(),
        },
        "main_session_contract": {
            "read_allowed": [
                str(state_path),
                str(result_path),
                str(pending_path),
                str(metrics_path),
                str(artifact_dir / "worker-checkpoint.json"),
                str(artifact_dir / "external-action.json"),
                str(artifact_dir / "external-result.json"),
                str(artifact_dir / "auto-decisions.jsonl"),
            ],
            "do_not_read_into_main_context": [
                str(artifact_dir / "worker-prompt.md"),
                str(artifact_dir / "worker-cli-output.log"),
                str(artifact_dir / "requirement-doc.md"),
                str(artifact_dir / "design-doc.md"),
                str(artifact_dir / "mcp-transparent-log.md"),
            ],
        },
        "issues": issues,
    }


def command_audit(args: argparse.Namespace) -> int:
    audit = audit_worker_isolation(Path(args.state))
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if args.strict and not audit.get("worker_isolation_ok"):
        return 1
    return 0


def parse_cli_json_output(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        return {"parsed": False, "messages": [], "result": None}

    try:
        data = json.loads(text)
        return {
            "parsed": True,
            "messages": data if isinstance(data, list) else [data],
            "result": data,
        }
    except json.JSONDecodeError:
        pass

    messages: list[Any] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {
        "parsed": bool(messages),
        "messages": messages,
        "result": messages[-1] if messages else None,
    }


def _deep_find_first(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key in keys:
            if key in value:
                return value[key]
        for item in value.values():
            found = _deep_find_first(item, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _deep_find_first(item, keys)
            if found is not None:
                return found
    return None


def build_worker_metrics(
    *,
    cmd: list[str],
    prompt_path: Path,
    log_path: Path,
    completed: subprocess.CompletedProcess[str],
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    stdout_classification: str,
    worker_subagents_enabled: bool,
    allowed_subagents: list[str],
) -> dict[str, Any]:
    parsed = parse_cli_json_output(completed.stdout or "")
    result = parsed.get("result")
    messages = parsed.get("messages") or []

    session_id = _deep_find_first(result, {"session_id", "sessionId"})
    total_cost = _deep_find_first(result, {"total_cost_usd", "totalCostUsd", "cost_usd"})
    num_turns = _deep_find_first(result, {"num_turns", "numTurns"})
    usage = _deep_find_first(result, {"usage", "modelUsage", "token_usage", "tokenUsage"})

    return {
        "is_worker": True,
        "worker_invocation": "claude -p",
        "session_isolation": "new claude -p invocation; no --resume or --continue is used; session persistence is disabled",
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration_seconds, 3),
        "returncode": completed.returncode,
        "command": cmd,
        "prompt_delivery": "stdin",
        "prompt_path": str(prompt_path),
        "log_path": str(log_path),
        "stdout_json_parsed": parsed.get("parsed", False),
        "stdout_classification": stdout_classification,
        "worker_subagents_enabled": worker_subagents_enabled,
        "allowed_subagents": allowed_subagents,
        "message_count": len(messages),
        "session_id": session_id,
        "num_turns": num_turns,
        "total_cost_usd": total_cost,
        "usage": usage,
        "raw_result_keys": sorted(result.keys()) if isinstance(result, dict) else [],
        "note": "Use /context inside an interactive Claude Code session for live context window usage; claude -p worker usage is captured here from CLI JSON when available.",
    }


def classify_worker_stdout(stdout: str) -> str:
    text = (stdout or "").strip()
    if not text:
        return "empty"
    lowered = text.lower()
    greeting_markers = ("你好", "您好", "hello", "hi", "我可以帮", "我能帮")
    artifact_markers = (
        "worker-result.json",
        "pending-questions.json",
        "requirement-handoff.json",
        "design-handoff.json",
        "STAGE_COMPLETED",
        "NEED_USER_INPUT",
        "VALIDATION_FAILED",
        "BLOCKED",
    )
    if len(text) < 200 and any(marker in lowered for marker in greeting_markers):
        return "likely_greeting_only"
    if any(marker.lower() in lowered for marker in artifact_markers):
        return "mentions_artifacts"
    return "unknown"


def run_worker_once(
    state_path: Path,
    *,
    output_format: str = "json",
    max_turns: int = 30,
    permission_mode: str | None = None,
    allowed_tools: str | None = None,
    mcp_config: str | None = None,
    enable_worker_subagents: bool = False,
) -> dict[str, Any]:
    state_path = state_path.resolve()
    state = load_state(state_path)
    artifact_dir = Path(state["artifact_dir"])
    subagents_enabled = bool(
        enable_worker_subagents
        or state.get("worker_subagents_enabled")
        or env_truthy("CLAUDE_WORKER_SUBAGENTS")
    )
    allowed_subagents = stage_subagent_names(state["current_stage"]) if subagents_enabled else []
    state["worker_subagents_enabled"] = subagents_enabled
    state["worker_subagents"] = allowed_subagents
    prompt_path = artifact_dir / "worker-prompt.md"
    prompt = make_worker_prompt(state)
    prompt_path.write_text(prompt, encoding="utf-8")
    result_path = artifact_dir / "worker-result.json"
    if result_path.exists():
        archive_path = artifact_dir / f"worker-result.previous-{_dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}.json"
        shutil.move(str(result_path), str(archive_path))
        add_history(state, "previous_worker_result_archived", {"from": str(result_path), "to": str(archive_path)})

    claude = shutil.which("claude")
    if not claude:
        raise SystemExit("claude CLI not found; run the prompt command and execute worker-prompt.md with an isolated worker manually")

    worker_permission_mode = permission_mode or os.environ.get("CLAUDE_WORKER_PERMISSION_MODE") or DEFAULT_WORKER_PERMISSION_MODE
    worker_allowed_tools = allowed_tools or os.environ.get("CLAUDE_WORKER_ALLOWED_TOOLS") or DEFAULT_WORKER_ALLOWED_TOOLS
    stage_skill = resolve_stage_skill(Path(state["project_root"]), state["current_stage"])
    config_dir = user_claude_config_dir()
    finalize_dir = None
    if isinstance(state.get("recovery_finalize"), dict) and state["recovery_finalize"].get("directory"):
        finalize_dir = Path(str(state["recovery_finalize"]["directory"])).resolve()
    access_dirs = []
    for path in [
        Path(state["project_root"]).resolve(),
        artifact_dir.resolve(),
        finalize_dir,
        stage_skill.parent.resolve(),
        config_dir.resolve() if config_dir.exists() else None,
        *input_access_dirs(state),
    ]:
        if path is None:
            continue
        if path not in access_dirs:
            access_dirs.append(path)
    cmd = [
        claude,
        "-p",
        "--input-format",
        "text",
        "--output-format",
        output_format,
        "--max-turns",
        str(max_turns),
        "--no-session-persistence",
        "--permission-mode",
        worker_permission_mode,
        "--add-dir",
        *[str(path) for path in access_dirs],
    ]
    worker_mcp_config = mcp_config or os.environ.get("CLAUDE_WORKER_MCP_CONFIG")
    if worker_mcp_config:
        cmd.extend(["--mcp-config", worker_mcp_config])
    if subagents_enabled and allowed_subagents:
        cmd.extend([
            "--agents",
            json.dumps(subagent_definitions_for(allowed_subagents), ensure_ascii=False),
        ])
    allowed_tool_args: list[str] = []
    if worker_allowed_tools:
        allowed_tool_args.append(worker_allowed_tools)
    if subagents_enabled and allowed_subagents:
        allowed_tool_args.append(f"Agent({','.join(allowed_subagents)})")
    if allowed_tool_args:
        cmd.append("--allowed-tools")
        cmd.extend(allowed_tool_args)
    started_at = now_iso()
    started_monotonic = time.monotonic()
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    completed = subprocess.run(
        cmd,
        cwd=state["project_root"],
        input=prompt,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
    )
    ended_at = now_iso()
    duration_seconds = time.monotonic() - started_monotonic
    log_path = artifact_dir / "worker-cli-output.log"
    log_path.write_text((completed.stdout or "") + ("\nSTDERR:\n" + completed.stderr if completed.stderr else ""), encoding="utf-8")
    stdout_classification = classify_worker_stdout(completed.stdout or "")
    metrics = build_worker_metrics(
        cmd=cmd,
        prompt_path=prompt_path,
        log_path=log_path,
        completed=completed,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration_seconds,
        stdout_classification=stdout_classification,
        worker_subagents_enabled=subagents_enabled,
        allowed_subagents=allowed_subagents,
    )
    metrics_path = artifact_dir / "worker-run-metrics.json"
    write_json(metrics_path, metrics)
    add_history(state, "worker_cli_run", {"returncode": completed.returncode, "log": str(log_path), "metrics": str(metrics_path), "stdout_classification": stdout_classification})
    save_state(state_path, state)
    return {
        "returncode": completed.returncode,
        "log": str(log_path),
        "metrics": str(metrics_path),
        "worker_proof": compact_worker_proof(metrics, metrics_path),
        "artifact_dir": str(artifact_dir),
        "worker_result": str(result_path),
        "stdout_classification": stdout_classification,
    }


def command_run_worker(args: argparse.Namespace) -> int:
    summary = run_worker_once(
        Path(args.state),
        output_format=args.output_format,
        max_turns=args.max_turns,
        permission_mode=args.permission_mode,
        allowed_tools=args.allowed_tools,
        mcp_config=args.mcp_config,
        enable_worker_subagents=args.enable_worker_subagents,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return int(summary["returncode"])


def command_step(args: argparse.Namespace) -> int:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    if state.get("stage_status") not in {"READY", "VALIDATION_FAILED"}:
        print(json.dumps({
            "state": str(state_path),
            "stage_status": state.get("stage_status"),
            "current_stage": state.get("current_stage"),
            "message": "state is not runnable; handle pending input, blocked state, or completion first",
        }, ensure_ascii=False, indent=2))
        return 0

    run_summary = run_worker_once(
        state_path,
        output_format=args.output_format,
        max_turns=args.max_turns,
        permission_mode=args.permission_mode,
        allowed_tools=args.allowed_tools,
        mcp_config=args.mcp_config,
        enable_worker_subagents=args.enable_worker_subagents,
    )
    result_path = Path(run_summary["worker_result"])
    if not result_path.exists():
        recovery = recover_missing_worker_result(state_path, run_summary)
        print(json.dumps({
            "run": run_summary,
            "recovery": recovery,
            "state": recovery.get("state", str(state_path)),
            "stage_status": recovery.get("stage_status", "BLOCKED"),
            "message": recovery.get("reason", "worker finished but worker-result.json was not created"),
        }, ensure_ascii=False, indent=2))
        return 0 if recovery.get("recovered") else 1

    record_summary = record_worker_result(state_path, result_path)
    print(json.dumps({
        "run": run_summary,
        "record": record_summary,
    }, ensure_ascii=False, indent=2))
    return int(run_summary["returncode"])


def command_run_loop(args: argparse.Namespace) -> int:
    state_path = Path(args.state).resolve()
    steps: list[dict[str, Any]] = []
    for index in range(args.max_steps):
        state = load_state(state_path)
        status = state.get("stage_status")
        if status == "NEED_USER_INPUT":
            auto_enabled = ai_confirmation_enabled_for_state(state, force_full_auto=bool(args.full_auto))
            if auto_enabled:
                auto_summary = run_auto_decision_worker(
                    state_path,
                    rounds=args.auto_decision_rounds or int(state.get("auto_decision_rounds", 3) or 3),
                    max_decisions=args.max_auto_decisions or int(state.get("max_auto_decisions", 20) or 20),
                    output_format=args.output_format,
                    max_turns=args.auto_decision_max_turns,
                    permission_mode=args.auto_decision_permission_mode,
                    allowed_tools=args.auto_decision_allowed_tools,
                )
                steps.append({"auto_decision": auto_summary})
                if auto_summary.get("resolved"):
                    continue
            break
        if status in {"BLOCKED", "COMPLETED"}:
            break
        if status not in {"READY", "VALIDATION_FAILED"}:
            break

        run_summary = run_worker_once(
            state_path,
            output_format=args.output_format,
            max_turns=args.max_turns,
            permission_mode=args.permission_mode,
            allowed_tools=args.allowed_tools,
            mcp_config=args.mcp_config,
            enable_worker_subagents=args.enable_worker_subagents,
        )
        result_path = Path(run_summary["worker_result"])
        if not result_path.exists():
            recovery = recover_missing_worker_result(state_path, run_summary)
            steps.append({
                "run": run_summary,
                "recovery": recovery,
                "message": recovery.get("reason", "worker finished but worker-result.json was not created"),
            })
            if recovery.get("recovered"):
                state_path = Path(recovery.get("state", str(state_path))).resolve()
                if recovery.get("stage_status") == "READY":
                    continue
                if recovery.get("stage_status") == "NEED_USER_INPUT":
                    auto_enabled = ai_confirmation_enabled_for_state(load_state(state_path), force_full_auto=bool(args.full_auto))
                    if auto_enabled:
                        continue
            break
        record_summary = record_worker_result(state_path, result_path)
        state_path = Path(record_summary["state"]).resolve()
        steps.append({"run": run_summary, "record": record_summary})

        next_state = load_state(state_path)
        if next_state.get("stage_status") == "NEED_USER_INPUT":
            auto_enabled = ai_confirmation_enabled_for_state(next_state, force_full_auto=bool(args.full_auto))
            if auto_enabled:
                continue
            break
        if next_state.get("stage_status") in {"BLOCKED", "COMPLETED"}:
            break

    final_state = load_state(state_path)
    print(json.dumps({
        "state": str(state_path),
        "final_stage_status": final_state.get("stage_status"),
        "current_stage": final_state.get("current_stage"),
        "steps": steps,
    }, ensure_ascii=False, indent=2))
    return 0


def command_auto_decide(args: argparse.Namespace) -> int:
    state = load_state(Path(args.state).resolve())
    summary = run_auto_decision_worker(
        Path(args.state),
        rounds=args.auto_decision_rounds or int(state.get("auto_decision_rounds", 3) or 3),
        max_decisions=args.max_auto_decisions or int(state.get("max_auto_decisions", 20) or 20),
        output_format=args.output_format,
        max_turns=args.auto_decision_max_turns,
        permission_mode=args.auto_decision_permission_mode,
        allowed_tools=args.auto_decision_allowed_tools,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("resolved") else 1


def command_metrics(args: argparse.Namespace) -> int:
    state = load_state(Path(args.state).resolve())
    artifact_dir = Path(state["artifact_dir"])
    metrics_path = Path(args.metrics).resolve() if args.metrics else artifact_dir / "worker-run-metrics.json"
    metrics = read_json(metrics_path)
    if not isinstance(metrics, dict):
        raise SystemExit(f"worker metrics not found or invalid: {metrics_path}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Claude Code workflow orchestration files.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_worker_run_options(worker_parser: argparse.ArgumentParser) -> None:
        worker_parser.add_argument("--output-format", default="json")
        worker_parser.add_argument("--max-turns", type=int, default=30)
        worker_parser.add_argument(
            "--permission-mode",
            default=None,
            help=(
                "Claude worker permission mode. Defaults to CLAUDE_WORKER_PERMISSION_MODE "
                f"or {DEFAULT_WORKER_PERMISSION_MODE}."
            ),
        )
        worker_parser.add_argument(
            "--allowed-tools",
            default=None,
            help=(
                "Comma-separated Claude tools/patterns to pre-allow for the worker. "
                "Defaults to CLAUDE_WORKER_ALLOWED_TOOLS or the orchestrator's write-capable default."
            ),
        )
        worker_parser.add_argument(
            "--mcp-config",
            default=None,
            help="Optional MCP config file for claude -p workers. Defaults to CLAUDE_WORKER_MCP_CONFIG when set.",
        )
        worker_parser.add_argument(
            "--enable-worker-subagents",
            action="store_true",
            help="Allow the worker to spawn stage-scoped read-only subagents for local research/review tasks.",
        )

    def add_auto_decision_options(auto_parser: argparse.ArgumentParser) -> None:
        auto_parser.add_argument("--auto-decision-rounds", type=int, default=None, help="Review rounds for AI auto decisions. Defaults to state value or 3.")
        auto_parser.add_argument("--max-auto-decisions", type=int, default=None, help="Maximum AI auto decisions for this command. Defaults to state value or 20.")
        auto_parser.add_argument("--auto-decision-max-turns", type=int, default=8, help="Max turns for the auto-decision claude -p worker.")
        auto_parser.add_argument("--auto-decision-permission-mode", default=None, help="Permission mode for the read-only auto-decision worker.")
        auto_parser.add_argument("--auto-decision-allowed-tools", default=None, help="Allowed tools for the auto-decision worker. Defaults to read-only tools.")

    p_init = sub.add_parser("init", help="Initialize a workflow state directory.")
    p_init.add_argument("--goal", default=None, help="Workflow goal. Optional when --url/--input-text/--input-file is provided; a default goal will be generated.")
    p_init.add_argument("--url", "--ticket-url", dest="url", help="Initial requirement ticket URL. Stored in workflow-input.json for requirement-analysis Mode A.")
    p_init.add_argument("--input-text", "--requirement", dest="input_text", help="Initial requirement text. Stored in workflow-input.json for requirement-analysis Mode B.")
    p_init.add_argument("--input-file", "--document", dest="input_file", help="Initial requirement document path. Stored in workflow-input.json for requirement-analysis Mode B.")
    p_init.add_argument("--source-type", default="auto", choices=["auto", "ticket_url", "manual_text", "document_file", "mixed", "goal_only"], help="Override initial input source type. Default infers from --url/--input-text/--input-file/--goal.")
    p_init.add_argument("--project-root")
    p_init.add_argument("--artifact-dir", "--artifacts-dir", dest="artifact_dir")
    p_init.add_argument("--run-id")
    p_init.add_argument("--no-reuse-existing", action="store_true", help="Always create a new workflow state instead of reusing a matching active one.")
    p_init.add_argument("--stage", default="requirement-analysis", choices=STAGES)
    p_init.add_argument("--max-retries", type=int, default=2)
    p_init.add_argument("--max-missing-result-recoveries", type=int, default=DEFAULT_MAX_MISSING_RESULT_RECOVERIES, help="Maximum recoveries for the same missing worker-result signature before BLOCKED.")
    p_init.add_argument("--auto-advance", action="store_true", help="Automatically enter the next stage after validation succeeds. Off by default.")
    p_init.add_argument("--full-auto", action="store_true", help="Use AI auto decisions for pending questions. Does not skip real external actions.")
    p_init.add_argument("--auto-confirm", action="store_true", help="Alias-style switch for AI auto decisions without changing stage auto-advance behavior.")
    p_init.add_argument("--manual-confirm-stages", help="Comma-separated stages that require user confirmation. Default: requirement-analysis. Example: requirement-analysis,design-phase")
    p_init.add_argument("--ai-confirm-stages", help="Comma-separated stages that should use AI confirmation instead of user confirmation.")
    p_init.add_argument("--auto-decision-rounds", type=int, default=3, help="Number of lightweight review rounds requested from the auto-decision worker.")
    p_init.add_argument("--max-auto-decisions", type=int, default=20, help="Maximum number of AI auto decisions for this workflow run.")
    p_init.add_argument("--enable-worker-subagents", action="store_true", help="Enable stage-scoped read-only subagents inside worker sessions.")
    p_init.set_defaults(func=command_init)

    p_prompt = sub.add_parser("prompt", help="Generate worker-prompt.md for the current stage.")
    p_prompt.add_argument("--state", required=True)
    p_prompt.set_defaults(func=command_prompt)

    p_add = sub.add_parser("add-decision", help="Append a user decision to decisions.jsonl.")
    p_add.add_argument("--state", required=True)
    p_add.add_argument("--question-batch-id", required=True)
    p_add.add_argument("--question-id", required=True)
    p_add.add_argument("--selected", required=True)
    p_add.add_argument("--free-text")
    p_add.add_argument("--decision-id")
    p_add.set_defaults(func=command_add_decision)

    p_record = sub.add_parser("record-result", help="Record worker-result.json into workflow state.")
    p_record.add_argument("--state", required=True)
    p_record.add_argument("--result", required=True)
    p_record.set_defaults(func=command_record_result)

    p_status = sub.add_parser("status", help="Print lightweight workflow status.")
    p_status.add_argument("--state")
    p_status.add_argument("--artifact-dir", "--artifacts-dir", dest="artifact_dir", help="Artifact directory containing workflow-state.json.")
    p_status.set_defaults(func=command_status)

    p_audit = sub.add_parser("audit", help="Audit whether the latest stage ran in an isolated claude -p worker.")
    p_audit.add_argument("--state", required=True)
    p_audit.add_argument("--strict", action="store_true", help="Exit with code 1 when worker isolation cannot be proven.")
    p_audit.set_defaults(func=command_audit)

    p_run = sub.add_parser("run-worker", help="Run claude -p with worker-prompt.md if the Claude CLI is available.")
    p_run.add_argument("--state", required=True)
    add_worker_run_options(p_run)
    p_run.set_defaults(func=command_run_worker)

    p_step = sub.add_parser("step", help="Run one worker, record worker-result.json, and advance workflow state.")
    p_step.add_argument("--state", required=True)
    add_worker_run_options(p_step)
    p_step.set_defaults(func=command_step)

    p_loop = sub.add_parser("run-loop", help="Run workers until user input, blocked state, completion, or max steps.")
    p_loop.add_argument("--state", required=True)
    p_loop.add_argument("--max-steps", type=int, default=5)
    p_loop.add_argument("--full-auto", action="store_true", help="Enable AI auto decisions for this run-loop invocation.")
    add_worker_run_options(p_loop)
    add_auto_decision_options(p_loop)
    p_loop.set_defaults(func=command_run_loop)

    p_auto = sub.add_parser("auto-decide", help="Resolve current pending-questions.json with an AI auto-decision worker.")
    p_auto.add_argument("--state", required=True)
    p_auto.add_argument("--output-format", default="json")
    add_auto_decision_options(p_auto)
    p_auto.set_defaults(func=command_auto_decide)

    p_metrics = sub.add_parser("metrics", help="Print latest worker-run-metrics.json.")
    p_metrics.add_argument("--state", required=True)
    p_metrics.add_argument("--metrics")
    p_metrics.set_defaults(func=command_metrics)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
