# -*- coding: utf-8 -*-

import argparse
import json
import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from jobs.import_swagger import import_swagger  # noqa: E402
from utils.identifier_utils import normalize_identifier  # noqa: E402
from utils.version_utils import sort_versions  # noqa: E402


logger = logging.getLogger(__name__)


def parse_version_file(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "--version must use DOC_VERSION=SWAGGER_FILE format."
        )

    doc_version, swagger_file = value.split("=", 1)
    doc_version = doc_version.strip()
    swagger_file = swagger_file.strip().strip('"')

    if not doc_version or not swagger_file:
        raise argparse.ArgumentTypeError(
            "--version must include both DOC_VERSION and SWAGGER_FILE."
        )

    return doc_version, swagger_file


def import_component_versions(
        component_id: str,
        version_files: list[tuple[str, str]],
        segment_id: str = "",
        segment_name: str = "",
        segment_description: str = "",
        segment_scene: str = "",
        component_name: str = "",
        component_description: str = "",
        component_scene: str = "",
        doc_url: str = "",
        product_id: str = "",
        product_version: str = "",
        product_name: str = "",
        product_description: str = "",
        component_version: str = "",
        enrichment_file: str | None = None,
        enrichment_files: dict[str, str] | None = None,
        enrichment_dir: str | None = None,
        path_prefix: str | None = None,
        allow_unbound: bool = False,
        rebuild_index: bool = False
):
    component_id = normalize_identifier(component_id)
    segment_id = normalize_identifier(segment_id)
    product_id = normalize_identifier(product_id)

    version_file_map = {
        doc_version: swagger_file
        for doc_version, swagger_file in version_files
    }
    ordered_doc_versions = sort_versions(
        list(version_file_map.keys())
    )
    enrichment_files = enrichment_files or {}
    if enrichment_dir:
        enrichment_path = Path(enrichment_dir)
        for doc_version in ordered_doc_versions:
            candidate = enrichment_path / f"{doc_version}.enrichment.json"
            if candidate.exists():
                enrichment_files.setdefault(
                    doc_version,
                    str(candidate)
                )
    summaries = []

    for doc_version in ordered_doc_versions:
        logger.info(
            "Importing %s %s from %s",
            component_id,
            doc_version,
            version_file_map[doc_version]
        )
        stats = import_swagger(
            component_id=component_id,
            doc_version=doc_version,
            swagger_file=version_file_map[doc_version],
            segment_id=segment_id,
            segment_name=segment_name,
            segment_description=segment_description,
            segment_scene=segment_scene,
            component_name=component_name,
            component_description=component_description,
            component_scene=component_scene,
            doc_url=doc_url,
            product_id=product_id,
            product_version=product_version,
            product_name=product_name,
            product_description=product_description,
            component_version=component_version,
            enrichment_file=enrichment_files.get(
                doc_version,
                enrichment_file
            ),
            path_prefix=path_prefix,
            allow_unbound=allow_unbound,
            rebuild_index=False
        )
        summaries.append({
            "doc_version": doc_version,
            "swagger_file": version_file_map[doc_version],
            "enrichment_file": enrichment_files.get(
                doc_version,
                enrichment_file
            ),
            "stats": stats
        })

    if rebuild_index:
        from jobs.rebuild_vector_indexes import rebuild_api_identity_index

        rebuild_api_identity_index()

    return {
        "component_id": component_id,
        "segment_id": segment_id,
        "imported_versions": summaries,
        "count": len(summaries),
        "vector_index_rebuilt": rebuild_index
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Import multiple Swagger/OpenAPI versions for one component into "
            "api_identity/api_contract knowledge tables."
        )
    )
    parser.add_argument("--component-id", required=True)
    parser.add_argument("--segment-id", default="")
    parser.add_argument("--segment-name", default="")
    parser.add_argument("--segment-description", default="")
    parser.add_argument("--segment-scene", default="")
    parser.add_argument(
        "--path-prefix",
        default=None,
        help=(
            "Override Swagger basePath/OpenAPI servers path for all imported files. "
            "Use an empty string to disable automatic prefixing."
        )
    )
    parser.add_argument(
        "--version",
        action="append",
        required=True,
        type=parse_version_file,
        help="Repeatable DOC_VERSION=SWAGGER_FILE pair, for example v1.0=docs/user-v1.json."
    )
    parser.add_argument("--component-name", default="")
    parser.add_argument("--component-description", default="")
    parser.add_argument("--component-scene", default="")
    parser.add_argument("--doc-url", default="")
    parser.add_argument("--product-id", default="")
    parser.add_argument("--product-version", default="")
    parser.add_argument("--product-name", default="")
    parser.add_argument("--product-description", default="")
    parser.add_argument("--component-version", default="")
    parser.add_argument("--enrichment-file", default=None)
    parser.add_argument(
        "--enrichment-dir",
        default=None,
        help=(
            "Directory containing DOC_VERSION.enrichment.json files. "
            "Used as a convenient alternative to repeated --enrichment-version."
        )
    )
    parser.add_argument(
        "--enrichment-version",
        action="append",
        default=[],
        type=parse_version_file,
        help=(
            "Repeatable DOC_VERSION=ENRICHMENT_FILE pair. "
            "When provided, it overrides --enrichment-file for that doc version."
        )
    )
    parser.add_argument(
        "--allow-unbound",
        action="store_true",
        help=(
            "Allow importing component/API docs without product baseline binding. "
            "Use only for experiments; MCP requirement lookup needs product binding."
        )
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild the API identity vector index after all versions are imported."
    )

    args = parser.parse_args()
    result = import_component_versions(
        component_id=args.component_id,
        version_files=args.version,
        segment_id=args.segment_id,
        segment_name=args.segment_name,
        segment_description=args.segment_description,
        segment_scene=args.segment_scene,
        component_name=args.component_name,
        component_description=args.component_description,
        component_scene=args.component_scene,
        doc_url=args.doc_url,
        product_id=args.product_id,
        product_version=args.product_version,
        product_name=args.product_name,
        product_description=args.product_description,
        component_version=args.component_version,
        enrichment_file=args.enrichment_file,
        enrichment_files=dict(args.enrichment_version),
        enrichment_dir=args.enrichment_dir,
        path_prefix=args.path_prefix,
        allow_unbound=args.allow_unbound,
        rebuild_index=args.rebuild_index
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    main()
