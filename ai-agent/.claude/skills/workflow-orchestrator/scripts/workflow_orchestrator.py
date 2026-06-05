#!/usr/bin/env python3
"""Lightweight orchestrator state helper for Claude Code worker workflows."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


STAGES = [
    "requirement-analysis",
    "design-phase",
    "prototype-design",
    "implementation",
    "self-test",
]

VALIDATION_BY_STAGE = {
    "requirement-analysis": "requirement-validation.json",
    "design-phase": "design-validation.json",
}

HANDOFF_BY_STAGE = {
    "requirement-analysis": "requirement-handoff.json",
    "design-phase": "design-handoff.json",
}


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False) + "\n")


def resolve_project_root(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    return Path.cwd().resolve()


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


def make_worker_prompt(state: dict[str, Any]) -> str:
    project_root = Path(state["project_root"])
    artifact_dir = Path(state["artifact_dir"])
    stage = state["current_stage"]
    decisions_log = artifact_dir / state.get("decisions_log", "decisions.jsonl")

    prior_handoff = state.get("latest_handoff") or ""
    stage_skill = project_root / ".claude" / "skills" / stage / "SKILL.md"
    result_path = artifact_dir / "worker-result.json"
    pending_path = artifact_dir / "pending-questions.json"
    state_path = artifact_dir / "workflow-state.json"

    if stage not in {"requirement-analysis", "design-phase"}:
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

    return f"""worker_mode: true
stage: {stage}
artifact_dir: {artifact_dir}
project_root: {project_root}

请使用这个 Claude Code skill：
{stage_skill}

必须读取：
- workflow-state: {state_path}
- decisions_log: {decisions_log}
- prior_handoff: {prior_handoff or "(requirement-analysis 首次执行可没有 prior_handoff)"}

交互规则：
- 不要直接向用户提问，不要调用 AskQuestion。
- 如果需要人工确认，写 {pending_path}，再写 {result_path}，status=NEED_USER_INPUT，然后停止。
- 如果 decisions_log 已经回答了当前确认点，使用该决策继续执行，并把证据写入阶段文档。

产物规则：
- 阶段产物必须写在 artifact_dir 或阶段 skill 指定的 requirements 产品目录下。
- 如果 requirement-analysis 识别出了产品目录，worker-result.json.artifact_dir 必须指向最终产品目录。
- 阶段完成后必须生成 {handoff_file} 和 {validation_file}。
- 阶段完成后必须运行对应 validator；validation success=false 时先自行修复一次，仍失败则 worker-result status=VALIDATION_FAILED。

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
        "decisions_log": "decisions.jsonl",
        "retry_count": 0,
        "max_retries": args.max_retries,
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
    state["stage_status"] = "READY"
    state["pending_questions"] = ""
    add_history(state, "decision_added", decision)
    save_state(state_path, state)
    print(json.dumps(decision, ensure_ascii=False, indent=2))
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


def command_record_result(args: argparse.Namespace) -> int:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    result_path = Path(args.result).resolve()
    result = read_json(result_path)
    if not isinstance(result, dict):
        raise SystemExit(f"worker result not found or invalid: {result_path}")

    status = result.get("status")
    artifact_dir = Path(result.get("artifact_dir") or state["artifact_dir"]).resolve()
    if artifact_dir != Path(state["artifact_dir"]).resolve():
        old_state_path = state_path
        state["artifact_dir"] = str(artifact_dir)
        artifact_dir.mkdir(parents=True, exist_ok=True)
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
        if ok is False:
            state["stage_status"] = "VALIDATION_FAILED"
            state["retry_count"] = int(state.get("retry_count", 0)) + 1
        else:
            following = next_stage(state["current_stage"])
            if following:
                state["current_stage"] = following
                state["current_phase"] = ""
                state["stage_status"] = "READY"
                state["retry_count"] = 0
            else:
                state["stage_status"] = "COMPLETED"
    else:
        raise SystemExit(f"unknown worker status: {status}")

    add_history(state, "worker_result_recorded", {"result": str(result_path), "status": status})
    save_state(state_path, state)
    print(json.dumps({"state": str(state_path), "stage_status": state["stage_status"], "current_stage": state["current_stage"]}, ensure_ascii=False, indent=2))
    return 0


def command_status(args: argparse.Namespace) -> int:
    state = load_state(Path(args.state).resolve())
    summary = {
        "workflow_goal": state.get("workflow_goal"),
        "artifact_dir": state.get("artifact_dir"),
        "current_stage": state.get("current_stage"),
        "current_phase": state.get("current_phase"),
        "stage_status": state.get("stage_status"),
        "latest_handoff": state.get("latest_handoff"),
        "latest_validation": state.get("latest_validation"),
        "pending_questions": state.get("pending_questions"),
        "retry_count": state.get("retry_count"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def command_run_worker(args: argparse.Namespace) -> int:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    artifact_dir = Path(state["artifact_dir"])
    prompt_path = artifact_dir / "worker-prompt.md"
    if not prompt_path.exists():
        prompt = make_worker_prompt(state)
        prompt_path.write_text(prompt, encoding="utf-8")

    claude = shutil.which("claude")
    if not claude:
        raise SystemExit("claude CLI not found; run the prompt command and execute worker-prompt.md with an isolated worker manually")

    prompt = prompt_path.read_text(encoding="utf-8")
    cmd = [claude, "-p", prompt, "--output-format", args.output_format, "--max-turns", str(args.max_turns)]
    completed = subprocess.run(cmd, cwd=state["project_root"], text=True, capture_output=True)
    log_path = artifact_dir / "worker-cli-output.log"
    log_path.write_text((completed.stdout or "") + ("\nSTDERR:\n" + completed.stderr if completed.stderr else ""), encoding="utf-8")
    add_history(state, "worker_cli_run", {"returncode": completed.returncode, "log": str(log_path)})
    save_state(state_path, state)
    print(json.dumps({"returncode": completed.returncode, "log": str(log_path)}, ensure_ascii=False, indent=2))
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Claude Code workflow orchestration files.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a workflow state directory.")
    p_init.add_argument("--goal", required=True)
    p_init.add_argument("--project-root")
    p_init.add_argument("--artifact-dir")
    p_init.add_argument("--run-id")
    p_init.add_argument("--stage", default="requirement-analysis", choices=STAGES)
    p_init.add_argument("--max-retries", type=int, default=2)
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

    p_run = sub.add_parser("run-worker", help="Run claude -p with worker-prompt.md if the Claude CLI is available.")
    p_run.add_argument("--state", required=True)
    p_run.add_argument("--output-format", default="json")
    p_run.add_argument("--max-turns", type=int, default=30)
    p_run.set_defaults(func=command_run_worker)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
