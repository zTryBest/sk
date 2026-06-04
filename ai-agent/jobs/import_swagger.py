# -*- coding: utf-8 -*-

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.design_phase import (  # noqa: E402
    ApiContract,
    ApiIdentity,
    ComponentCatalog,
    ComponentDocVersion,
    ComponentSegment,
    ProductComponentBaseline,
)
from repository.design_repository import DesignRepository  # noqa: E402
from utils.identifier_utils import normalize_identifier  # noqa: E402


HTTP_METHODS = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "options",
}

logger = logging.getLogger(__name__)


def load_json(path: str) -> dict[str, Any]:
    with open(
            path,
            "r",
            encoding="utf-8"
    ) as f:
        return json.load(f)


def local_ref(root: dict[str, Any], ref: str):
    if not ref.startswith("#/"):
        return {"$ref": ref}

    current = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        current = current[part]

    return current


def resolve_schema(
        root: dict[str, Any],
        schema: Any,
        depth: int = 0
):
    if depth > 5:
        return schema

    if isinstance(schema, dict):
        if "$ref" in schema:
            return resolve_schema(
                root,
                local_ref(root, schema["$ref"]),
                depth + 1
            )

        return {
            key: resolve_schema(root, value, depth + 1)
            for key, value in schema.items()
        }

    if isinstance(schema, list):
        return [
            resolve_schema(root, item, depth + 1)
            for item in schema
        ]

    return schema


def compact_schema(schema: Any):
    if not isinstance(schema, dict):
        return schema or {}

    if "type" in schema:
        result = {
            "type": schema.get("type")
        }
        if "properties" in schema:
            result["properties"] = {
                key: compact_schema(value)
                for key, value in schema["properties"].items()
            }
        if "items" in schema:
            result["items"] = compact_schema(
                schema["items"]
            )
        if "required" in schema:
            result["required"] = schema["required"]
        return result

    if "properties" in schema:
        return {
            "type": "object",
            "properties": {
                key: compact_schema(value)
                for key, value in schema["properties"].items()
            },
            "required": schema.get("required", [])
        }

    return schema


def merge_parameters(
        path_item: dict[str, Any],
        operation: dict[str, Any]
) -> list[dict[str, Any]]:
    return list(path_item.get("parameters") or []) + list(
        operation.get("parameters") or []
    )


def schema_from_parameters(
        root: dict[str, Any],
        parameters: list[dict[str, Any]]
):
    result = {
        "path": {},
        "query": {},
        "header": {},
        "body": {}
    }
    lines = []

    for param in parameters:
        name = param.get("name", "")
        location = param.get("in", "")
        required = param.get("required", False)
        description = param.get("description", "")

        if location == "body":
            schema = compact_schema(
                resolve_schema(
                    root,
                    param.get("schema") or {}
                )
            )
            result["body"] = schema
            lines.append(
                f"{name or 'body'}: {description}".strip()
            )
            continue

        schema = param.get("schema") or {
            "type": param.get("type", "string")
        }

        if location in result:
            result[location][name] = {
                "required": required,
                "schema": compact_schema(
                    resolve_schema(root, schema)
                ),
                "description": description
            }

        if name:
            lines.append(
                f"{name}: {description}".strip()
            )

    return result, "\n".join(lines)


def request_body_from_openapi3(
        root: dict[str, Any],
        operation: dict[str, Any]
):
    request_body = operation.get("requestBody") or {}
    content = request_body.get("content") or {}
    json_media = (
        content.get("application/json")
        or next(iter(content.values()), {})
    )
    schema = compact_schema(
        resolve_schema(
            root,
            json_media.get("schema") or {}
        )
    )
    return schema


def response_schema(
        root: dict[str, Any],
        operation: dict[str, Any]
):
    responses = operation.get("responses") or {}
    response = (
        responses.get("200")
        or responses.get("201")
        or responses.get("default")
        or next(iter(responses.values()), {})
    )

    if "content" in response:
        content = response.get("content") or {}
        media = (
            content.get("application/json")
            or next(iter(content.values()), {})
        )
        return compact_schema(
            resolve_schema(
                root,
                media.get("schema") or {}
            )
        )

    return compact_schema(
        resolve_schema(
            root,
            response.get("schema") or {}
        )
    )


def response_demo(operation: dict[str, Any]):
    responses = operation.get("responses") or {}
    response = (
        responses.get("200")
        or responses.get("201")
        or responses.get("default")
        or next(iter(responses.values()), {})
    )
    examples = response.get("examples") or {}

    if "application/json" in examples:
        return json.dumps(
            examples["application/json"],
            ensure_ascii=False
        )

    content = response.get("content") or {}
    for media in content.values():
        example = media.get("example")
        if example is not None:
            return json.dumps(
                example,
                ensure_ascii=False
            )
        examples = media.get("examples") or {}
        if examples:
            first = next(iter(examples.values()))
            value = first.get("value", first)
            return json.dumps(
                value,
                ensure_ascii=False
            )

    return ""


def operation_key(method: str, path: str):
    return f"{method.upper()} {path}"


def normalize_path(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return ""
    return "/" + path.strip("/")


def join_paths(prefix: str, path: str) -> str:
    prefix = normalize_path(prefix)
    path = normalize_path(path)

    if not prefix:
        return path or "/"
    if not path or path == "/":
        return prefix
    return f"{prefix.rstrip('/')}/{path.lstrip('/')}"


def openapi3_server_path(swagger: dict[str, Any]) -> str:
    servers = swagger.get("servers") or []
    if not servers:
        return ""

    first_server = servers[0] or {}
    url = first_server.get("url", "")
    if not url:
        return ""

    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return parsed.path or ""

    return url


def swagger_path_prefix(
        swagger: dict[str, Any],
        path_prefix: str | None = None
) -> str:
    if path_prefix is not None:
        return path_prefix

    if swagger.get("basePath"):
        return swagger.get("basePath") or ""

    if str(swagger.get("openapi", "")).startswith("3"):
        return openapi3_server_path(swagger)

    return ""


def load_enrichment(path: str | None):
    if not path:
        return {}

    payload = load_json(path)
    return payload.get("operations", payload)


def parse_operations(
        swagger: dict[str, Any],
        enrichment: dict[str, Any],
        path_prefix: str | None = None
):
    operations = []
    paths = swagger.get("paths") or {}
    is_openapi3 = str(swagger.get("openapi", "")).startswith("3")
    prefix = swagger_path_prefix(
        swagger,
        path_prefix=path_prefix
    )

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue

            if not isinstance(operation, dict):
                continue

            full_path = join_paths(
                prefix,
                path
            )
            key = operation_key(method, full_path)
            extra = enrichment.get(key, {})

            parameters = merge_parameters(
                path_item,
                operation
            )
            request_schema, params_desc = schema_from_parameters(
                swagger,
                parameters
            )

            if is_openapi3:
                body_schema = request_body_from_openapi3(
                    swagger,
                    operation
                )
                if body_schema:
                    request_schema["body"] = body_schema

            api_name = (
                extra.get("api_name")
                or operation.get("summary")
                or operation.get("operationId")
                or key
            )
            description = (
                extra.get("description")
                or operation.get("description")
                or operation.get("summary")
                or ""
            )
            tags = (
                extra.get("capability_tags")
                or operation.get("tags")
                or []
            )
            scene = extra.get("scene", "")
            usage_note_parts = [
                extra.get("usage_notes", "")
            ]
            for extra_key in (
                    "business_terms",
                    "search_keywords",
                    "request_field_notes",
                    "response_field_notes",
                    "request_value_notes",
                    "response_value_notes"
            ):
                extra_value = extra.get(extra_key)
                if not extra_value:
                    continue
                usage_note_parts.append(
                    f"{extra_key}: {json.dumps(extra_value, ensure_ascii=False)}"
                )
            usage_notes = "\n".join(
                item
                for item in usage_note_parts
                if item
            )

            parsed_response_schema = response_schema(
                swagger,
                operation
            )

            operations.append({
                "key": key,
                "method": method.upper(),
                "path": full_path,
                "raw_path": path,
                "path_prefix": prefix,
                "api_name": api_name,
                "description": description,
                "capability_tags": tags,
                "scene": scene,
                "params_desc": extra.get("params_desc") or params_desc,
                "request_schema": extra.get("request_schema") or request_schema,
                "response_schema": extra.get("response_schema") or parsed_response_schema,
                "request_headers": extra.get("request_headers", {}),
                "request_example": extra.get("request_example", {}),
                "response_example": extra.get("response_example", {}),
                "response_demo": (
                    extra.get("response_demo")
                    or response_demo(operation)
                ),
                "usage_notes": usage_notes,
                "source_url": extra.get("source_url", "")
            })

    return operations


def emit_enrichment_template(
        swagger_file: str,
        output_file: str,
        path_prefix: str | None = None
):
    swagger = load_json(swagger_file)
    operations = parse_operations(
        swagger,
        enrichment={},
        path_prefix=path_prefix
    )
    template = {
        "operations": {
            item["key"]: {
                "api_name": item["api_name"],
                "capability_tags": item["capability_tags"],
                "scene": item["scene"],
                "description": item["description"],
                "business_terms": [],
                "search_keywords": [],
                "request_field_notes": {},
                "response_field_notes": {},
                "request_value_notes": {},
                "response_value_notes": {},
                "params_desc": item["params_desc"],
                "request_example": item["request_example"],
                "response_example": item["response_example"],
                "response_demo": item["response_demo"],
                "usage_notes": item["usage_notes"]
            }
            for item in operations
        }
    }
    with open(
            output_file,
            "w",
            encoding="utf-8"
    ) as f:
        json.dump(
            template,
            f,
            ensure_ascii=False,
            indent=2
        )


def import_swagger(
        component_id: str,
        doc_version: str,
        swagger_file: str,
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
        path_prefix: str | None = None,
        allow_unbound: bool = False,
        rebuild_index: bool = False
):
    component_id = normalize_identifier(component_id)
    segment_id = normalize_identifier(segment_id)
    product_id = normalize_identifier(product_id)

    if (
            not allow_unbound
            and not (
                product_id
                and product_version
                and component_version
            )
    ):
        raise ValueError(
            "导入接口知识必须绑定平台基线，请提供 --product-id、"
            "--product-version、--component-version；如果只是实验性导入，"
            "请显式增加 --allow-unbound。"
        )

    repo = DesignRepository()
    swagger = load_json(swagger_file)
    enrichment = load_enrichment(enrichment_file)
    operations = parse_operations(
        swagger,
        enrichment,
        path_prefix=path_prefix
    )

    if component_name or component_description or component_scene:
        repo.upsert_component(
            ComponentCatalog(
                component_id=component_id,
                component_name=component_name or component_id,
                description=component_description,
                scene=component_scene
            )
        )

    if segment_id:
        repo.upsert_component_segment(
            ComponentSegment(
                component_id=component_id,
                segment_id=segment_id,
                segment_name=segment_name or segment_id,
                description=segment_description,
                scene=segment_scene
            )
        )

    if product_id and product_version:
        repo.upsert_product_release(
            product_id=product_id,
            product_version=product_version,
            product_name=product_name,
            description=product_description
        )
        repo.upsert_product_component_baseline(
            ProductComponentBaseline(
                product_id=product_id,
                product_version=product_version,
                component_id=component_id,
                component_version=component_version or doc_version
            )
        )

    repo.upsert_component_doc_version(
        ComponentDocVersion(
            component_id=component_id,
            segment_id=segment_id,
            doc_version=doc_version,
            doc_url=doc_url,
            crawl_status="SUCCESS"
        )
    )

    current_keys = set()
    stats = {
        "component_id": component_id,
        "segment_id": segment_id,
        "path_prefix": swagger_path_prefix(
            swagger,
            path_prefix=path_prefix
        ),
        "operations": len(operations),
        "identities_upserted": 0,
        "contracts_inserted_or_updated": 0,
        "unchanged_contracts": 0,
        "removed_apis": 0
    }

    for operation in operations:
        current_keys.add(
            (
                operation["method"],
                operation["path"]
            )
        )
        identity_id = repo.upsert_api_identity(
            ApiIdentity(
                component_id=component_id,
                segment_id=segment_id,
                method=operation["method"],
                api_path=operation["path"],
                api_name=operation["api_name"],
                capability_tags=operation["capability_tags"],
                scene=operation["scene"],
                description=operation["description"]
            )
        )
        stats["identities_upserted"] += 1

        contract = ApiContract(
            api_identity_id=identity_id,
            doc_version=doc_version,
            params_desc=operation["params_desc"],
            request_schema=operation["request_schema"],
            response_schema=operation["response_schema"],
            request_headers=operation["request_headers"],
            request_example=operation["request_example"],
            response_example=operation["response_example"],
            response_demo=operation["response_demo"],
            usage_notes=operation["usage_notes"],
            source_url=operation["source_url"] or doc_url
        )
        current_hash = DesignRepository._contract_hash(
            contract
        )
        existing_contract = repo.get_api_contract(
            api_identity_id=identity_id,
            doc_version=doc_version
        )
        previous_contract = repo.get_latest_contract_before(
            api_identity_id=identity_id,
            doc_version=doc_version
        )

        if existing_contract:
            repo.upsert_api_contract(contract)
            change_type = (
                "UNCHANGED"
                if DesignRepository._contract_hash(existing_contract) == current_hash
                else "CHANGED"
            )
            stats["contracts_inserted_or_updated"] += 1
        elif previous_contract and (
                DesignRepository._contract_hash(previous_contract) == current_hash
        ):
            change_type = "UNCHANGED"
            stats["unchanged_contracts"] += 1
        else:
            repo.upsert_api_contract(contract)
            change_type = (
                "ADDED"
                if previous_contract is None
                else "CHANGED"
            )
            stats["contracts_inserted_or_updated"] += 1

        repo.upsert_api_lifecycle(
            api_identity_id=identity_id,
            doc_version=doc_version,
            status="PRESENT",
            change_type=change_type
        )

    for identity in repo.list_api_identities_for_component(
            component_id=component_id,
            segment_id=segment_id
    ):
        key = (
            identity.method.upper(),
            identity.api_path
        )
        if key in current_keys:
            continue
        repo.upsert_api_lifecycle(
            api_identity_id=identity.id,
            doc_version=doc_version,
            status="REMOVED",
            change_type="REMOVED"
        )
        stats["removed_apis"] += 1

    if rebuild_index:
        from jobs.rebuild_vector_indexes import rebuild_api_identity_index

        rebuild_api_identity_index()
        stats["vector_index_rebuilt"] = True
    else:
        stats["vector_index_rebuilt"] = False

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Import Swagger/OpenAPI JSON into api_identity/api_contract knowledge tables."
    )
    parser.add_argument("--component-id", required=True)
    parser.add_argument("--doc-version", required=True)
    parser.add_argument("--swagger-file", required=True)
    parser.add_argument("--segment-id", default="")
    parser.add_argument("--segment-name", default="")
    parser.add_argument("--segment-description", default="")
    parser.add_argument("--segment-scene", default="")
    parser.add_argument(
        "--path-prefix",
        default=None,
        help=(
            "Override Swagger basePath/OpenAPI servers path. "
            "Use an empty string to disable automatic prefixing."
        )
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
    parser.add_argument("--emit-enrichment-template", default="")
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
        help="Rebuild the API identity vector index after import."
    )

    args = parser.parse_args()

    if args.emit_enrichment_template:
        emit_enrichment_template(
            swagger_file=args.swagger_file,
            output_file=args.emit_enrichment_template,
            path_prefix=args.path_prefix
        )
        print(
            json.dumps(
                {
                    "message": "enrichment template generated",
                    "output_file": args.emit_enrichment_template
                },
                ensure_ascii=False,
                indent=2
            )
        )
        return

    stats = import_swagger(
        component_id=args.component_id,
        doc_version=args.doc_version,
        swagger_file=args.swagger_file,
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
        path_prefix=args.path_prefix,
        allow_unbound=args.allow_unbound,
        rebuild_index=args.rebuild_index
    )

    print(
        json.dumps(
            stats,
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
