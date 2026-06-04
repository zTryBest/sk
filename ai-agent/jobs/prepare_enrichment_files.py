# -*- coding: utf-8 -*-

import argparse
import json
import re
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from jobs.import_swagger import emit_enrichment_template  # noqa: E402


VERSION_PATTERN = re.compile(
    r"(v?\d+(?:[._-]\d+)*(?:[._-]?(?:RELEASE|SNAPSHOT|FINAL))?)",
    re.IGNORECASE,
)


def infer_doc_version(path: Path) -> str:
    stem = path.stem
    if stem.lower().endswith(".swagger"):
        stem = stem[:-8]
    if stem.lower().endswith(".openapi"):
        stem = stem[:-8]

    matches = VERSION_PATTERN.findall(stem)
    if matches:
        return matches[-1].replace("_", ".")
    return stem


def find_swagger_files(swagger_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in swagger_dir.glob("*.json")
        if path.is_file()
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate audit-ready enrichment templates for all Swagger/OpenAPI "
            "JSON files in a directory."
        )
    )
    parser.add_argument("--swagger-dir", required=True)
    parser.add_argument("--enrichment-dir", required=True)
    parser.add_argument(
        "--path-prefix",
        default=None,
        help=(
            "Override Swagger basePath/OpenAPI servers path for all files. "
            "Use an empty string to disable automatic prefixing."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing enrichment files.",
    )

    args = parser.parse_args()
    swagger_dir = Path(args.swagger_dir)
    enrichment_dir = Path(args.enrichment_dir)
    enrichment_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not swagger_dir.exists():
        raise FileNotFoundError(
            f"swagger dir not found: {swagger_dir}"
        )

    files = find_swagger_files(
        swagger_dir
    )
    result = {
        "swagger_dir": str(swagger_dir),
        "enrichment_dir": str(enrichment_dir),
        "count": len(files),
        "items": [],
    }

    for swagger_file in files:
        doc_version = infer_doc_version(
            swagger_file
        )
        output_file = enrichment_dir / f"{doc_version}.enrichment.json"
        status = "generated"
        if output_file.exists() and not args.overwrite:
            status = "skipped_existing"
        else:
            emit_enrichment_template(
                swagger_file=str(swagger_file),
                output_file=str(output_file),
                path_prefix=args.path_prefix,
            )

        result["items"].append({
            "doc_version": doc_version,
            "swagger_file": str(swagger_file),
            "enrichment_file": str(output_file),
            "status": status,
            "version_arg": f"{doc_version}={swagger_file}",
            "enrichment_arg": f"{doc_version}={output_file}",
        })

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
