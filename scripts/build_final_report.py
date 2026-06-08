#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build artifacts/08_final_report.md from stage artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path


ARTIFACTS = [
    "01_requirement.json",
    "02_solution.json",
    "03_prototype.html",
    "04_plan.json",
    "05_backend_report.md",
    "06_frontend_report.md",
    "07_test_report.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build final delivery report.")
    parser.add_argument("--artifacts", default="artifacts")
    parser.add_argument("--output", default="artifacts/08_final_report.md")
    args = parser.parse_args()

    artifact_dir = Path(args.artifacts)
    output = Path(args.output)
    lines = ["# 最终交付报告", "", "## 阶段产物", ""]
    for name in ARTIFACTS:
        path = artifact_dir / name
        status = "存在" if path.exists() else "缺失"
        lines.append(f"- `{path}`: {status}")
    lines.extend(["", "## 结论", "", "请由 ReviewAgent 根据测试报告和阶段产物补充最终交付结论。", ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
