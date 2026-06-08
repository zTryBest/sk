#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download and extract a Java backend scaffold from the HTTP scaffold service."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile
from io import BytesIO
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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_endpoint(value: str) -> str:
    endpoint = value.strip()
    if not endpoint:
        raise ValueError("scaffold service URL is required")
    if endpoint.endswith("/v1/frame/frame"):
        return endpoint
    return endpoint.rstrip("/") + "/v1/frame/frame"


def split_service_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_config_info(args: argparse.Namespace) -> list[dict[str, Any]]:
    values = {
        "database": (args.database, args.database_has),
        "cache": (args.cache, args.cache_has),
        "mq": (args.mq, args.mq_has),
        "reference": (args.reference, args.reference_has),
        "javaVersion": (args.java_version, args.java_version_has),
        "basicFeatures": (args.basic_features, args.basic_features_has),
        "controller": (args.controller, args.controller_has),
    }
    return [{"label": label, "value": value, "has": has} for label, (value, has) in values.items()]


def build_request(args: argparse.Namespace) -> dict[str, Any]:
    if args.request_json:
        with Path(args.request_json).open("r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("--request-json must contain a JSON object")
        return data

    missing = [
        name
        for name, value in {
            "--component-id": args.component_id,
            "--version": args.version,
            "--service-id": args.service_id,
        }.items()
        if not str(value or "").strip()
    ]
    if missing:
        raise ValueError(f"missing required scaffold request values: {', '.join(missing)}")

    return {
        "configInfo": build_config_info(args),
        "version": args.version,
        "packageName": args.package_name,
        "componentId": args.component_id,
        "serviceId": split_service_ids(args.service_id),
        "port": args.port,
        "errorCode": args.error_code,
        "dependenciesVersion": args.dependencies_version,
        "email": args.email,
        "author": args.author,
    }


def post_zip(endpoint: str, payload: dict[str, Any], timeout: int) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"scaffold service returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"scaffold service is unavailable: {exc.reason}") from exc

    if status < 200 or status >= 300:
        raise RuntimeError(f"scaffold service returned HTTP {status}")
    if not zipfile.is_zipfile(BytesIO(data)):
        preview = data[:200].decode("utf-8", errors="replace")
        raise RuntimeError(f"scaffold response is not a zip stream; content-type={content_type!r}; preview={preview!r}")
    return data


def safe_extract(zip_bytes: bytes, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    root = output_dir.resolve()
    extracted: list[str] = []

    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        for info in archive.infolist():
            if not info.filename or info.filename.endswith("/"):
                continue
            destination = (root / info.filename).resolve()
            if root != destination and root not in destination.parents:
                raise RuntimeError(f"unsafe zip entry outside output dir: {info.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, destination.open("wb") as dst:
                dst.write(src.read())
            extracted.append(str(destination))

    return extracted


def detect_build_tool(path: Path) -> str:
    if (path / "pom.xml").exists():
        return "maven"
    if (path / "build.gradle").exists() or (path / "build.gradle.kts").exists() or (path / "settings.gradle").exists():
        return "gradle"
    return "unknown"


def find_source_dir(output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    if detect_build_tool(output_dir) != "unknown":
        return output_dir

    children = [item for item in output_dir.iterdir() if item.is_dir()]
    build_roots = [item for item in children if detect_build_tool(item) != "unknown"]
    if len(build_roots) == 1:
        return build_roots[0]

    nested_roots: list[Path] = []
    for marker in ("pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"):
        nested_roots.extend(path.parent for path in output_dir.rglob(marker))
    unique = []
    seen: set[Path] = set()
    for item in nested_roots:
        resolved = item.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    if unique:
        return sorted(unique, key=lambda item: len(item.parts))[0]

    if len(children) == 1:
        return children[0]
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Java scaffold source code from the HTTP scaffold service.")
    parser.add_argument(
        "--url",
        default=os.environ.get("SCAFFOLD_SERVICE_URL", ""),
        help="Scaffold service base URL or full endpoint. Full endpoint is http://<ip>:8888/v1/frame/frame.",
    )
    parser.add_argument("--output-dir", required=True, help="Directory where the zip stream is extracted.")
    parser.add_argument("--manifest", default="", help="Manifest path. Defaults to <output-dir>/scaffold-manifest.json.")
    parser.add_argument("--request-json", default="", help="Optional exact scaffold request JSON file.")
    parser.add_argument("--print-request", action="store_true", help="Print the request JSON and exit without HTTP.")
    parser.add_argument("--timeout", type=int, default=120, help="HTTP timeout seconds.")

    parser.add_argument("--database", default="postgresql")
    parser.add_argument("--cache", default="jedis")
    parser.add_argument("--mq", default="kafka")
    parser.add_argument("--reference", default="bic,bic;bic,xauthc;bic,xauthz")
    parser.add_argument("--java-version", default="11")
    parser.add_argument("--basic-features", default="cas")
    parser.add_argument("--controller", default="")
    parser.add_argument("--database-has", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cache-has", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--mq-has", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reference-has", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--java-version-has", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--basic-features-has", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--controller-has", action=argparse.BooleanOptionalAction, default=False)

    parser.add_argument("--version", default=os.environ.get("SCAFFOLD_COMPONENT_VERSION", ""))
    parser.add_argument("--package-name", default=os.environ.get("SCAFFOLD_PACKAGE_NAME", "com.aries.jc.sc"))
    parser.add_argument("--component-id", default=os.environ.get("SCAFFOLD_COMPONENT_ID", ""))
    parser.add_argument("--service-id", default=os.environ.get("SCAFFOLD_SERVICE_ID", ""))
    parser.add_argument("--port", type=int, default=17000)
    parser.add_argument("--error-code", default="0x160a")
    parser.add_argument("--dependencies-version", default="3.4.3")
    parser.add_argument("--email", default="z@cn")
    parser.add_argument("--author", default="z")
    return parser


def main() -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args()

    try:
        payload = build_request(args)
        if args.print_request:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        endpoint = normalize_endpoint(args.url)
        output_dir = Path(args.output_dir).resolve()
        manifest_path = Path(args.manifest).resolve() if args.manifest else output_dir / "scaffold-manifest.json"

        zip_bytes = post_zip(endpoint, payload, args.timeout)
        extracted = safe_extract(zip_bytes, output_dir)
        source_dir = find_source_dir(output_dir)
        manifest = {
            "schema_version": "1.0",
            "generated_at": now_iso(),
            "service_url": endpoint,
            "request": payload,
            "output_dir": str(output_dir),
            "source_dir": str(source_dir),
            "build_tool": detect_build_tool(source_dir),
            "response_summary": {
                "type": "zip_stream",
                "bytes": len(zip_bytes),
                "extracted_files_count": len(extracted),
            },
        }
        write_json(manifest_path, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
