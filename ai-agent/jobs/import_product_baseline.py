# -*- coding: utf-8 -*-

import argparse
import json
import sys
from pathlib import Path
from typing import Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.design_phase import ComponentCatalog, ProductComponentBaseline  # noqa: E402
from repository.design_repository import DesignRepository  # noqa: E402
from utils.identifier_utils import normalize_identifier  # noqa: E402
from utils.version_utils import find_nearest_doc_version  # noqa: E402


def _load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_component_pair(value: str) -> dict[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "--component must use COMPONENT_ID=COMPONENT_VERSION format."
        )
    component_id, component_version = value.split("=", 1)
    component_id = component_id.strip()
    component_version = component_version.strip()
    if not component_id or not component_version:
        raise argparse.ArgumentTypeError(
            "--component must include both component id and version."
        )
    return {
        "component_id": component_id,
        "component_version": component_version,
    }


def _baseline_from_file(path: str) -> dict[str, Any]:
    payload = _load_json(path)
    components = payload.get("components", [])
    if not isinstance(components, list):
        raise ValueError("baseline file field 'components' must be a list.")
    return payload


def _component_doc_resolution(
        repo: DesignRepository,
        component_id: str,
        component_version: str,
) -> list[dict[str, Any]]:
    rows = repo.list_component_doc_version_rows(
        component_id=component_id,
        segment_id=None,
    )
    segment_versions: dict[str, list[str]] = {}
    for row in rows:
        segment_id = row.get("segment_id", "") or ""
        segment_versions.setdefault(
            segment_id,
            []
        ).append(
            row["doc_version"]
        )

    result = []
    for segment_id, doc_versions in segment_versions.items():
        resolved = find_nearest_doc_version(
            component_version=component_version,
            doc_versions=doc_versions,
        )
        result.append({
            "segment_id": segment_id,
            "doc_versions": doc_versions,
            "resolved_doc_version": resolved["doc_version"],
            "match_level": resolved["match_level"],
            "confidence": resolved["confidence"],
            "risk": resolved["risk"],
        })
    return result


def import_product_baseline(
        product_id: str,
        product_version: str,
        components: list[dict[str, Any]],
        product_name: str = "",
        product_description: str = "",
        source: str = "BASELINE",
        dry_run: bool = False,
) -> dict[str, Any]:
    product_id = normalize_identifier(
        product_id
    )
    repo = DesignRepository()

    normalized_components = []
    for item in components:
        component_id = normalize_identifier(
            item["component_id"]
        )
        component_version = item["component_version"]
        normalized_components.append({
            "component_id": component_id,
            "component_version": component_version,
            "component_name": item.get("component_name", ""),
            "component_description": (
                item.get("component_description")
                or item.get("description", "")
            ),
            "component_scene": (
                item.get("component_scene")
                or item.get("scene", "")
            ),
            "source": item.get("source", source),
            "doc_resolution": _component_doc_resolution(
                repo=repo,
                component_id=component_id,
                component_version=component_version,
            ),
        })

    result = {
        "mode": "DRY_RUN" if dry_run else "EXECUTE",
        "product_id": product_id,
        "product_version": product_version,
        "product_name": product_name,
        "component_count": len(normalized_components),
        "components": normalized_components,
        "warnings": [],
    }

    for item in normalized_components:
        if not item["doc_resolution"]:
            result["warnings"].append(
                {
                    "component_id": item["component_id"],
                    "message": (
                        "No component_doc_version rows found. "
                        "Import Swagger/OpenAPI docs before using MCP lookup."
                    ),
                }
            )

    if dry_run:
        return result

    product_release_id = repo.upsert_product_release(
        product_id=product_id,
        product_version=product_version,
        product_name=product_name,
        description=product_description,
    )
    result["product_release_id"] = product_release_id

    baseline_rows = []
    for item in normalized_components:
        if (
                item["component_name"]
                or item["component_description"]
                or item["component_scene"]
        ):
            repo.upsert_component(
                ComponentCatalog(
                    component_id=item["component_id"],
                    component_name=(
                        item["component_name"]
                        or item["component_id"]
                    ),
                    description=item["component_description"],
                    scene=item["component_scene"],
                )
            )

        baseline_id = repo.upsert_product_component_baseline(
            ProductComponentBaseline(
                product_id=product_id,
                product_version=product_version,
                component_id=item["component_id"],
                component_version=item["component_version"],
                source=item["source"],
            )
        )
        baseline_rows.append({
            "baseline_id": baseline_id,
            "component_id": item["component_id"],
            "component_version": item["component_version"],
        })

    result["baseline_rows"] = baseline_rows
    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Import a product version baseline: product release plus a batch "
            "of component id/version bindings."
        )
    )
    parser.add_argument("--product-id", default="")
    parser.add_argument("--product-version", default="")
    parser.add_argument("--product-name", default="")
    parser.add_argument("--product-description", default="")
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        type=_parse_component_pair,
        help="Repeatable COMPONENT_ID=COMPONENT_VERSION pair.",
    )
    parser.add_argument(
        "--baseline-file",
        default="",
        help=(
            "JSON file with product_id/product_version/product_name and "
            "components list."
        ),
    )
    parser.add_argument("--source", default="BASELINE")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned baseline rows and doc-version resolution only.",
    )

    args = parser.parse_args()
    file_payload = (
        _baseline_from_file(args.baseline_file)
        if args.baseline_file
        else {}
    )

    product_id = args.product_id or file_payload.get("product_id", "")
    product_version = (
        args.product_version
        or file_payload.get("product_version", "")
    )
    product_name = args.product_name or file_payload.get("product_name", "")
    product_description = (
        args.product_description
        or file_payload.get("product_description", "")
        or file_payload.get("description", "")
    )
    components = list(file_payload.get("components", []))
    components.extend(args.component)

    if not product_id or not product_version:
        raise ValueError(
            "product_id and product_version are required."
        )
    if not components:
        raise ValueError(
            "At least one component is required."
        )

    result = import_product_baseline(
        product_id=product_id,
        product_version=product_version,
        product_name=product_name,
        product_description=product_description,
        components=components,
        source=args.source,
        dry_run=args.dry_run,
    )
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
