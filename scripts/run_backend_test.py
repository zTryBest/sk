#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run available backend tests under workspace/backend."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def pick_command(root: Path) -> list[str] | None:
    if (root / "mvnw.cmd").exists():
        return [str(root / "mvnw.cmd"), "test"]
    if (root / "mvnw").exists():
        return [str(root / "mvnw"), "test"]
    if (root / "pom.xml").exists():
        return ["mvn", "test"]
    if (root / "gradlew.bat").exists():
        return [str(root / "gradlew.bat"), "test"]
    if (root / "gradlew").exists():
        return [str(root / "gradlew"), "test"]
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        return ["gradle", "test"]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run backend tests.")
    parser.add_argument("--root", default="workspace/backend")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    command = pick_command(root)
    if not command:
        print(f"No Maven/Gradle test command found under {root}")
        return 1
    print(f"Running: {' '.join(command)}")
    completed = subprocess.run(command, cwd=root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
