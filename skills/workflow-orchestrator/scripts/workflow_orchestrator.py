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
    "Bash(python *)",
    "Bash(py *)",
])

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
- 如果错误涉及 pending markers、待确认、open_questions、UNDECIDED、target_object_resolution.status=open、缺少用户决策、缺少产品/版本、缺少数据库类型、候选 API 选择等事实不足或人工确认问题，禁止自行替换字段，必须写 pending-questions.json 和 worker-result.json(status=NEED_USER_INPUT) 后停止。
- 只有纯文档结构、验收标准数量不足、字段遗漏但不需要新业务事实的问题，才允许 worker 基于已知需求自行补充并重新运行 validator。
- 如果不确定某个 validation error 是否需要用户确认，按 NEED_USER_INPUT 处理。
- 阶段边界不要询问“是否继续下一阶段”；阶段完成且 validator success=true 时直接写 worker-result.json(status=STAGE_COMPLETED)。是否进入下一阶段由 orchestrator 在主 session 中通过 pending-questions.json 统一确认。
"""
    stage_specific_notes = ""
    if stage == "requirement-analysis":
        stage_specific_notes = """
阶段特别注意：
- 如果 workflow_goal 或输入材料中包含 ticket URL，必须按 requirement-analysis/SKILL.md 的 Mode A 执行。
- WebFetch 或轻量抓取失败、跳转 SSO、403、超时或内容为空时，必须自动切换到 Playwright MCP 或浏览器抓取；不要把轻量抓取失败当作阶段失败。
- 只有需要用户完成 SSO 登录、缺少平台名称/版本、或存在关键澄清点时，才写 pending-questions.json。
"""
    elif stage == "design-phase":
        stage_specific_notes = """
阶段特别注意：
- 必须优先读取 requirement-handoff.json；不要依赖 workflow_goal 或聊天历史补事实。
- MCP 只检索平台上下文动作，不检索外部执行动作。
- 架构、中间件、实现方式分类、MCP 检索计划、候选 API 选择等确认点，在 worker 模式下都写 pending-questions.json。
"""
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
- decisions_log: {decisions_log}
- prior_handoff: {prior_handoff or "(requirement-analysis 首次执行可没有 prior_handoff)"}

{stage_specific_notes}

{subagent_notes}

交互规则：
- 不要直接向用户提问，不要调用 AskQuestion。
- 如果需要人工确认，先写 worker-checkpoint.json，再写 {pending_path}，再写 {result_path}，status=NEED_USER_INPUT，然后停止。
- 如果 decisions_log 已经回答了当前确认点，使用该决策继续执行，并把证据写入阶段文档。
- 如果遇到 SSO、人机验证、文件选择、外部系统操作、长时间人工处理或任何 worker 不能保留的有状态资源，不能依赖当前 worker 的浏览器、MCP 连接、临时进程或内存状态等待用户。写 worker-checkpoint.json、external-action.json 和 pending-questions.json，要求主流程完成外部动作并写 external-result.json；等 decisions_log 记录对应 resume_decision_id 后，读取 worker-checkpoint.json 和 external-result.json 断点继续。
- worker 每次启动时都必须先检查 worker-checkpoint.json、external-result.json 和 decisions_log。如果存在已完成的外部动作或用户决策，必须从 checkpoint 恢复，不要从头重复已完成步骤。

产物规则：
- 阶段产物必须写在 artifact_dir 或阶段 skill 指定的 requirements 产品目录下。
- 如果 requirement-analysis 识别出了产品目录，worker-result.json.artifact_dir 必须指向最终产品目录。
- 阶段完成后必须生成 {handoff_file} 和 {validation_file}。
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
    run_id = args.run_id or _dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    artifact_dir = Path(args.artifact_dir).resolve() if args.artifact_dir else default_artifact_dir(project_root, run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "schema_version": "1.0",
        "workflow_goal": args.goal,
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
        "auto_advance_stages": bool(args.auto_advance),
        "worker_subagents_enabled": bool(args.enable_worker_subagents),
        "worker_subagents": stage_subagent_names(args.stage) if args.enable_worker_subagents else [],
        "history": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    add_history(state, "initialized", {"stage": args.stage})
    state_path = state_path_from_artifact(artifact_dir)
    write_json(state_path, state)
    (artifact_dir / "decisions.jsonl").touch(exist_ok=True)
    print(json.dumps({"state": str(state_path), "artifact_dir": str(artifact_dir)}, ensure_ascii=False, indent=2))
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


def command_add_decision(args: argparse.Namespace) -> int:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    artifact_dir = Path(state["artifact_dir"])
    decision = {
        "decision_id": args.decision_id or f"D-{_dt.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "question_batch_id": args.question_batch_id,
        "question_id": args.question_id,
        "selected": args.selected,
        "free_text": args.free_text or "",
        "decided_by": "user",
        "decided_at": now_iso(),
    }
    append_jsonl(artifact_dir / state.get("decisions_log", "decisions.jsonl"), decision)
    pending_next_stage = state.get("pending_next_stage") or ""
    completed_stage = state.get("completed_stage_waiting_approval") or state.get("current_stage", "")
    if pending_next_stage and args.question_id == f"workflow.advance_to.{pending_next_stage}":
        selected = (args.selected or "").lower()
        if selected in {"approve", "continue", "yes", "y"}:
            state["current_stage"] = pending_next_stage
            state["current_phase"] = ""
            state["stage_status"] = "READY"
            state["retry_count"] = 0
            add_history(state, "stage_boundary_approved", {"from": completed_stage, "to": pending_next_stage})
        elif selected in {"revise", "rework", "modify", "no", "n"}:
            state["current_stage"] = completed_stage
            state["current_phase"] = ""
            state["stage_status"] = "READY"
            state["retry_count"] = 0
            add_history(state, "stage_boundary_revision_requested", {"stage": completed_stage, "next_stage": pending_next_stage})
        else:
            state["stage_status"] = "BLOCKED"
            add_history(state, "stage_boundary_stopped", {"stage": completed_stage, "next_stage": pending_next_stage, "selected": args.selected})
        state["pending_next_stage"] = ""
        state["completed_stage_waiting_approval"] = ""
    else:
        state["stage_status"] = "READY"
    state["pending_questions"] = ""
    add_history(state, "decision_added", decision)
    save_state(state_path, state)
    print(json.dumps({
        "decision": decision,
        "state": str(state_path),
        "stage_status": state["stage_status"],
        "current_stage": state["current_stage"],
        "resume_worker_required": state["stage_status"] == "READY",
        "next_internal_action": "call run-loop; do not execute the stage inside the main session",
    }, ensure_ascii=False, indent=2))
    return 0


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


def command_record_result(args: argparse.Namespace) -> int:
    summary = record_worker_result(Path(args.state), Path(args.result))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def command_status(args: argparse.Namespace) -> int:
    state = load_state(Path(args.state).resolve())
    artifact_dir = Path(state.get("artifact_dir") or ".")
    metrics_path = artifact_dir / "worker-run-metrics.json"
    metrics = read_json(metrics_path, {}) if metrics_path.exists() else {}
    checkpoint_path = artifact_dir / "worker-checkpoint.json"
    external_action_path = artifact_dir / "external-action.json"
    external_result_path = artifact_dir / "external-result.json"
    summary = {
        "workflow_goal": state.get("workflow_goal"),
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
        "worker_subagents_enabled": state.get("worker_subagents_enabled", False),
        "worker_subagents": state.get("worker_subagents", []),
        "checkpoint": str(checkpoint_path) if checkpoint_path.exists() else "",
        "external_action": str(external_action_path) if external_action_path.exists() else "",
        "external_result": str(external_result_path) if external_result_path.exists() else "",
        "retry_count": state.get("retry_count"),
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

    claude = shutil.which("claude")
    if not claude:
        raise SystemExit("claude CLI not found; run the prompt command and execute worker-prompt.md with an isolated worker manually")

    worker_permission_mode = permission_mode or os.environ.get("CLAUDE_WORKER_PERMISSION_MODE") or DEFAULT_WORKER_PERMISSION_MODE
    worker_allowed_tools = allowed_tools or os.environ.get("CLAUDE_WORKER_ALLOWED_TOOLS") or DEFAULT_WORKER_ALLOWED_TOOLS
    stage_skill = resolve_stage_skill(Path(state["project_root"]), state["current_stage"])
    access_dirs = []
    for path in [
        Path(state["project_root"]).resolve(),
        artifact_dir.resolve(),
        stage_skill.parent.resolve(),
    ]:
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
        "worker_result": str(artifact_dir / "worker-result.json"),
        "stdout_classification": stdout_classification,
    }


def command_run_worker(args: argparse.Namespace) -> int:
    summary = run_worker_once(
        Path(args.state),
        output_format=args.output_format,
        max_turns=args.max_turns,
        permission_mode=args.permission_mode,
        allowed_tools=args.allowed_tools,
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
        enable_worker_subagents=args.enable_worker_subagents,
    )
    result_path = Path(run_summary["worker_result"])
    if not result_path.exists():
        state = load_state(state_path)
        state["stage_status"] = "BLOCKED"
        add_history(state, "worker_result_missing", {"run": run_summary})
        save_state(state_path, state)
        print(json.dumps({
            "run": run_summary,
            "state": str(state_path),
            "stage_status": "BLOCKED",
            "message": "worker finished but worker-result.json was not created",
        }, ensure_ascii=False, indent=2))
        return 1

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
        if status in {"NEED_USER_INPUT", "BLOCKED", "COMPLETED"}:
            break
        if status not in {"READY", "VALIDATION_FAILED"}:
            break

        run_summary = run_worker_once(
            state_path,
            output_format=args.output_format,
            max_turns=args.max_turns,
            permission_mode=args.permission_mode,
            allowed_tools=args.allowed_tools,
            enable_worker_subagents=args.enable_worker_subagents,
        )
        result_path = Path(run_summary["worker_result"])
        if not result_path.exists():
            state = load_state(state_path)
            state["stage_status"] = "BLOCKED"
            add_history(state, "worker_result_missing", {"run": run_summary})
            save_state(state_path, state)
            steps.append({
                "run": run_summary,
                "message": "worker finished but worker-result.json was not created",
            })
            break
        record_summary = record_worker_result(state_path, result_path)
        state_path = Path(record_summary["state"]).resolve()
        steps.append({"run": run_summary, "record": record_summary})

        next_state = load_state(state_path)
        if next_state.get("stage_status") in {"NEED_USER_INPUT", "BLOCKED", "COMPLETED"}:
            break

    final_state = load_state(state_path)
    print(json.dumps({
        "state": str(state_path),
        "final_stage_status": final_state.get("stage_status"),
        "current_stage": final_state.get("current_stage"),
        "steps": steps,
    }, ensure_ascii=False, indent=2))
    return 0


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
            "--enable-worker-subagents",
            action="store_true",
            help="Allow the worker to spawn stage-scoped read-only subagents for local research/review tasks.",
        )

    p_init = sub.add_parser("init", help="Initialize a workflow state directory.")
    p_init.add_argument("--goal", required=True)
    p_init.add_argument("--project-root")
    p_init.add_argument("--artifact-dir")
    p_init.add_argument("--run-id")
    p_init.add_argument("--stage", default="requirement-analysis", choices=STAGES)
    p_init.add_argument("--max-retries", type=int, default=2)
    p_init.add_argument("--auto-advance", action="store_true", help="Automatically enter the next stage after validation succeeds. Off by default.")
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
    p_status.add_argument("--state", required=True)
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
    add_worker_run_options(p_loop)
    p_loop.set_defaults(func=command_run_loop)

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
