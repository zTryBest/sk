#!/usr/bin/env python3
"""Lightweight orchestrator state helper for Claude Code worker workflows."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
import time
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
    workflow_goal = state.get("workflow_goal", "")

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
    validation_policy = """
校验失败处理规则：
- 不要把 validation errors 机械改成通过。先判断错误类型。
- 如果错误涉及 pending markers、待确认、open_questions、UNDECIDED、target_object_resolution.status=open、缺少用户决策、缺少产品/版本、缺少数据库类型、候选 API 选择等事实不足或人工确认问题，禁止自行替换字段，必须写 pending-questions.json 和 worker-result.json(status=NEED_USER_INPUT) 后停止。
- 只有纯文档结构、验收标准数量不足、字段遗漏但不需要新业务事实的问题，才允许 worker 基于已知需求自行补充并重新运行 validator。
- 如果不确定某个 validation error 是否需要用户确认，按 NEED_USER_INPUT 处理。
- 阶段边界不要询问“是否继续下一阶段”；阶段完成且 validator success=true 时直接写 worker-result.json(status=STAGE_COMPLETED)，由 orchestrator 自动流转。
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

必须读取的运行文件：
- workflow-state: {state_path}
- decisions_log: {decisions_log}
- prior_handoff: {prior_handoff or "(requirement-analysis 首次执行可没有 prior_handoff)"}

{stage_specific_notes}

交互规则：
- 不要直接向用户提问，不要调用 AskQuestion。
- 如果需要人工确认，写 {pending_path}，再写 {result_path}，status=NEED_USER_INPUT，然后停止。
- 如果 decisions_log 已经回答了当前确认点，使用该决策继续执行，并把证据写入阶段文档。

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
        "session_isolation": "new claude -p invocation; no --resume or --continue is used by the orchestrator",
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration_seconds, 3),
        "returncode": completed.returncode,
        "command": cmd,
        "prompt_path": str(prompt_path),
        "log_path": str(log_path),
        "stdout_json_parsed": parsed.get("parsed", False),
        "message_count": len(messages),
        "session_id": session_id,
        "num_turns": num_turns,
        "total_cost_usd": total_cost,
        "usage": usage,
        "raw_result_keys": sorted(result.keys()) if isinstance(result, dict) else [],
        "note": "Use /context inside an interactive Claude Code session for live context window usage; claude -p worker usage is captured here from CLI JSON when available.",
    }


def run_worker_once(
    state_path: Path,
    *,
    output_format: str = "json",
    max_turns: int = 30,
) -> dict[str, Any]:
    state_path = state_path.resolve()
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
    cmd = [claude, "-p", prompt, "--output-format", output_format, "--max-turns", str(max_turns)]
    started_at = now_iso()
    started_monotonic = time.monotonic()
    completed = subprocess.run(cmd, cwd=state["project_root"], text=True, capture_output=True)
    ended_at = now_iso()
    duration_seconds = time.monotonic() - started_monotonic
    log_path = artifact_dir / "worker-cli-output.log"
    log_path.write_text((completed.stdout or "") + ("\nSTDERR:\n" + completed.stderr if completed.stderr else ""), encoding="utf-8")
    metrics = build_worker_metrics(
        cmd=cmd,
        prompt_path=prompt_path,
        log_path=log_path,
        completed=completed,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration_seconds,
    )
    metrics_path = artifact_dir / "worker-run-metrics.json"
    write_json(metrics_path, metrics)
    add_history(state, "worker_cli_run", {"returncode": completed.returncode, "log": str(log_path), "metrics": str(metrics_path)})
    save_state(state_path, state)
    return {
        "returncode": completed.returncode,
        "log": str(log_path),
        "metrics": str(metrics_path),
        "artifact_dir": str(artifact_dir),
        "worker_result": str(artifact_dir / "worker-result.json"),
    }


def command_run_worker(args: argparse.Namespace) -> int:
    summary = run_worker_once(
        Path(args.state),
        output_format=args.output_format,
        max_turns=args.max_turns,
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
    )
    result_path = Path(run_summary["worker_result"])
    if not result_path.exists():
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
        )
        result_path = Path(run_summary["worker_result"])
        if not result_path.exists():
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

    p_step = sub.add_parser("step", help="Run one worker, record worker-result.json, and advance workflow state.")
    p_step.add_argument("--state", required=True)
    p_step.add_argument("--output-format", default="json")
    p_step.add_argument("--max-turns", type=int, default=30)
    p_step.set_defaults(func=command_step)

    p_loop = sub.add_parser("run-loop", help="Run workers until user input, blocked state, completion, or max steps.")
    p_loop.add_argument("--state", required=True)
    p_loop.add_argument("--output-format", default="json")
    p_loop.add_argument("--max-turns", type=int, default=30)
    p_loop.add_argument("--max-steps", type=int, default=5)
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
