# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os
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

DEFAULT_IGNORED_REQUEST_HEADERS = {
    "authorization",
    "token",
    "access-token",
    "access_token",
    "accesstoken",
    "x-access-token",
    "x-auth-token",
    "bearer",
}


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
        depth: int = 0,
        seen_refs: set[str] | None = None
):
    if depth > 20:
        return schema
    if seen_refs is None:
        seen_refs = set()

    if isinstance(schema, dict):
        if "$ref" in schema:
            ref = schema["$ref"]
            if ref in seen_refs:
                return {
                    "$ref": ref,
                    "circular_ref": True
                }
            branch_seen_refs = set(
                seen_refs
            )
            branch_seen_refs.add(ref)
            resolved = resolve_schema(
                root,
                local_ref(root, ref),
                depth + 1,
                branch_seen_refs
            )
            siblings = {
                key: value
                for key, value in schema.items()
                if key != "$ref"
            }
            if siblings and isinstance(resolved, dict):
                merged = dict(resolved)
                merged.update(
                    resolve_schema(
                        root,
                        siblings,
                        depth + 1,
                        branch_seen_refs
                    )
                )
                return merged
            return resolved

        if "allOf" in schema:
            merged = {
                key: value
                for key, value in schema.items()
                if key != "allOf"
            }
            merged_properties = dict(
                merged.get("properties") or {}
            )
            merged_required = list(
                merged.get("required") or []
            )
            for item in schema.get("allOf") or []:
                resolved = resolve_schema(
                    root,
                    item,
                    depth + 1,
                    seen_refs
                )
                if not isinstance(resolved, dict):
                    continue
                merged_properties.update(
                    resolved.get("properties") or {}
                )
                for field in resolved.get("required") or []:
                    if field not in merged_required:
                        merged_required.append(field)
                for key, value in resolved.items():
                    if key not in {
                            "properties",
                            "required"
                    }:
                        merged.setdefault(
                            key,
                            value
                        )
            if merged_properties:
                merged["properties"] = merged_properties
            if merged_required:
                merged["required"] = merged_required
            return resolve_schema(
                root,
                merged,
                depth + 1,
                seen_refs
            )

        return {
            key: resolve_schema(
                root,
                value,
                depth + 1,
                seen_refs
            )
            for key, value in schema.items()
        }

    if isinstance(schema, list):
        return [
            resolve_schema(
                root,
                item,
                depth + 1,
                seen_refs
            )
            for item in schema
        ]

    return schema


def compact_schema(schema: Any):
    if isinstance(schema, list):
        return [
            compact_schema(item)
            for item in schema
        ]

    if not isinstance(schema, dict):
        return schema or {}

    result = {}
    schema_type = schema.get("type")
    if not schema_type:
        if "properties" in schema:
            schema_type = "object"
        elif "items" in schema:
            schema_type = "array"
    if schema_type:
        result["type"] = schema_type

    for key in (
            "format",
            "title",
            "description",
            "enum",
            "default",
            "example",
            "maximum",
            "minimum",
            "maxLength",
            "minLength",
            "pattern",
            "maxItems",
            "minItems",
            "collectionFormat",
            "nullable",
            "circular_ref"
    ):
        if key in schema:
            result[key] = schema[key]

    if "properties" in schema:
        result["properties"] = {
                key: compact_schema(value)
                for key, value in schema["properties"].items()
        }
    if "items" in schema:
        result["items"] = compact_schema(
            schema["items"]
        )
    if "additionalProperties" in schema:
        result["additionalProperties"] = compact_schema(
            schema["additionalProperties"]
        )
    if "required" in schema:
        result["required"] = schema["required"]
    for key in (
            "oneOf",
            "anyOf"
    ):
        if key in schema:
            result[key] = compact_schema(
                schema[key]
            )

    return result or schema


def schema_type_name(schema: Any) -> str:
    if not isinstance(schema, dict):
        return type(schema).__name__
    if schema.get("type"):
        return schema["type"]
    if "properties" in schema:
        return "object"
    if "items" in schema:
        return "array"
    return "unknown"


def collect_schema_fields(
        schema: Any,
        prefix: str = "",
        limit: int = 200
) -> list[dict[str, Any]]:
    fields = []

    def walk(
            node: Any,
            path: str,
            required: bool = False
    ):
        if len(fields) >= limit:
            return
        if not isinstance(node, dict) or not node:
            return

        node_type = schema_type_name(node)
        if path:
            fields.append({
                "path": path,
                "type": node_type,
                "required": required,
                "description": node.get("description", ""),
                "format": node.get("format", ""),
                "enum": node.get("enum", []),
                "example": node.get("example", ""),
                "constraints": {
                    key: node[key]
                    for key in (
                        "maximum",
                        "minimum",
                        "maxLength",
                        "minLength",
                        "pattern",
                        "maxItems",
                        "minItems"
                    )
                    if key in node
                }
            })

        if "properties" in node:
            required_fields = set(
                node.get("required") or []
            )
            for name, child in (node.get("properties") or {}).items():
                child_path = (
                    f"{path}.{name}"
                    if path
                    else name
                )
                walk(
                    child,
                    child_path,
                    name in required_fields
                )
        if "items" in node:
            item_path = (
                f"{path}[]"
                if path
                else "[]"
            )
            walk(
                node["items"],
                item_path,
                required
            )
        if isinstance(node.get("additionalProperties"), dict):
            additional_path = (
                f"{path}{{}}"
                if path
                else "{}"
            )
            walk(
                node["additionalProperties"],
                additional_path,
                required
            )

    walk(
        schema,
        prefix
    )
    return fields


def collect_request_fields(
        request_schema: dict[str, Any],
        sections: tuple[str, ...] = (
            "path",
            "query"
        ),
        include_body: bool = True,
        limit: int = 200
) -> list[dict[str, Any]]:
    fields = []

    for section in sections:
        for name, meta in (request_schema.get(section) or {}).items():
            schema = meta.get("schema") or {}
            fields.append({
                "path": f"{section}.{name}",
                "type": schema_type_name(schema),
                "required": bool(meta.get("required")),
                "description": meta.get("description", ""),
                "format": (
                    schema.get("format", "")
                    if isinstance(schema, dict)
                    else ""
                ),
                "enum": (
                    schema.get("enum", [])
                    if isinstance(schema, dict)
                    else []
                ),
                "example": (
                    schema.get("example", "")
                    if isinstance(schema, dict)
                    else ""
                ),
                "constraints": (
                    {
                        key: schema[key]
                        for key in (
                            "maximum",
                            "minimum",
                            "maxLength",
                            "minLength",
                            "pattern",
                            "maxItems",
                            "minItems"
                        )
                        if key in schema
                    }
                    if isinstance(schema, dict)
                    else {}
                )
            })
            if len(fields) >= limit:
                return fields
            nested_fields = collect_schema_fields(
                schema,
                prefix=f"{section}.{name}",
                limit=limit - len(fields)
            )
            fields.extend(
                nested_fields[1:]
                if nested_fields
                and nested_fields[0]["path"] == f"{section}.{name}"
                else nested_fields
            )
            if len(fields) >= limit:
                return fields

    if include_body:
        body_schema = request_schema.get("body") or {}
        body_meta = request_schema.get("body_meta") or {}
        body_name = body_meta.get("name", "")
        body_prefix = (
            f"body.{body_name}"
            if body_name and body_name != "body"
            else "body"
        )
        if body_meta:
            fields.append({
                "path": body_prefix,
                "type": schema_type_name(body_schema),
                "required": bool(body_meta.get("required")),
                "description": body_meta.get("description", ""),
                "format": "",
                "enum": [],
                "example": "",
                "constraints": {}
            })
        nested_body_fields = collect_schema_fields(
            body_schema,
            prefix=body_prefix,
            limit=limit - len(fields)
        )
        if body_meta and nested_body_fields:
            nested_body_fields = nested_body_fields[1:]
        fields.extend(
            nested_body_fields
        )
    return fields[:limit]


def collect_request_header_fields(
        request_schema: dict[str, Any],
        limit: int = 100
) -> list[dict[str, Any]]:
    return collect_request_fields(
        request_schema=request_schema,
        sections=("header",),
        include_body=False,
        limit=limit
    )


def has_unresolved_ref(schema: Any) -> bool:
    if isinstance(schema, dict):
        if "$ref" in schema:
            return True
        return any(
            has_unresolved_ref(value)
            for value in schema.values()
        )
    if isinstance(schema, list):
        return any(
            has_unresolved_ref(item)
            for item in schema
        )
    return False


def schema_description_ratio(fields: list[dict[str, Any]]) -> float:
    if not fields:
        return 0.0
    described = sum(
        1
        for field in fields
        if field.get("description")
    )
    return round(
        described / len(fields),
        4
    )


def contract_quality(
        method: str,
        request_schema: dict[str, Any],
        response_schema_value: dict[str, Any],
        request_fields: list[dict[str, Any]],
        response_fields: list[dict[str, Any]]
) -> dict[str, Any]:
    score = 1.0
    reasons = []

    method = method.upper()
    has_request_fields = bool(request_fields)
    has_response_fields = bool(response_fields)

    if method in {
            "POST",
            "PUT",
            "PATCH"
    } and not has_request_fields:
        score -= 0.35
        reasons.append("request parameters are not explicit")
    if not has_response_fields:
        score -= 0.35
        reasons.append("response schema is empty or unclear")
    if has_unresolved_ref(request_schema) or has_unresolved_ref(response_schema_value):
        score -= 0.25
        reasons.append("schema contains unresolved $ref")

    request_description_ratio = schema_description_ratio(
        request_fields
    )
    response_description_ratio = schema_description_ratio(
        response_fields
    )
    if has_request_fields and request_description_ratio < 0.3:
        score -= 0.15
        reasons.append("request fields lack descriptions")
    if has_response_fields and response_description_ratio < 0.3:
        score -= 0.15
        reasons.append("response fields lack descriptions")

    return {
        "contract_confidence": max(
            0.0,
            round(score, 2)
        ),
        "request_description_ratio": request_description_ratio,
        "response_description_ratio": response_description_ratio,
        "reasons": reasons
    }


def field_note_seed(fields: list[dict[str, Any]]) -> dict[str, str]:
    return {
        field["path"]: field.get("description", "")
        for field in fields
        if field.get("path")
    }


def ignored_request_headers() -> set[str]:
    configured = os.getenv(
        "SWAGGER_IGNORED_REQUEST_HEADERS",
        ""
    )
    if not configured:
        return set(
            DEFAULT_IGNORED_REQUEST_HEADERS
        )
    return {
        item.strip().lower()
        for item in configured.split(",")
        if item.strip()
    }


def is_ignored_request_header(
        name: str,
        ignored_headers: set[str] | None = None
) -> bool:
    ignored_headers = (
        ignored_headers
        if ignored_headers is not None
        else ignored_request_headers()
    )
    normalized = (name or "").strip().lower()
    return normalized in ignored_headers


def merge_parameters(
        path_item: dict[str, Any],
        operation: dict[str, Any]
) -> list[dict[str, Any]]:
    return list(path_item.get("parameters") or []) + list(
        operation.get("parameters") or []
    )


def scalar_parameter_schema(param: dict[str, Any]) -> dict[str, Any]:
    schema = dict(
        param.get("schema") or {}
    )
    if not schema:
        schema["type"] = param.get("type", "string")

    for key in (
            "format",
            "enum",
            "default",
            "example",
            "maximum",
            "minimum",
            "maxLength",
            "minLength",
            "pattern",
            "maxItems",
            "minItems",
            "collectionFormat",
            "items"
    ):
        if key in param and key not in schema:
            schema[key] = param[key]

    return schema


def schema_from_parameters(
        root: dict[str, Any],
        parameters: list[dict[str, Any]]
):
    result = {
        "path": {},
        "query": {},
        "header": {},
        "body": {},
        "body_meta": {}
    }
    lines = []
    header_lines = []
    ignored_headers = ignored_request_headers()

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
            result["body_meta"] = {
                "name": name or "body",
                "required": required,
                "description": description
            }
            if description:
                lines.append(
                    f"body.{name or 'body'}: {description}".strip()
                )
            continue

        schema = scalar_parameter_schema(
            param
        )

        if (
                location == "header"
                and is_ignored_request_header(
                    name,
                    ignored_headers
                )
        ):
            continue

        if location in result:
            result[location][name] = {
                "required": required,
                "schema": compact_schema(
                    resolve_schema(root, schema)
                ),
                "description": description
            }

        if name:
            line = f"{location}.{name}: {description}".strip()
            if location == "header":
                header_lines.append(line)
            else:
                lines.append(line)

    return result, "\n".join(lines), "\n".join(header_lines)


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
            request_schema, params_desc, header_desc = schema_from_parameters(
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
                    "request_header_notes",
                    "response_field_notes",
                    "request_value_notes",
                    "request_header_value_notes",
                    "response_value_notes",
                    "header_desc",
                    "contract_confidence",
                    "contract_quality",
                    "confidence_reason",
                    "schema_analysis",
                    "validation_notes"
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
            request_schema_final = (
                extra.get("request_schema")
                or request_schema
            )
            response_schema_final = (
                extra.get("response_schema")
                or parsed_response_schema
            )
            request_fields = collect_request_fields(
                request_schema_final
            )
            request_header_fields = collect_request_header_fields(
                request_schema_final
            )
            response_fields = collect_schema_fields(
                response_schema_final,
                prefix="response"
            )
            quality = contract_quality(
                method=method,
                request_schema=request_schema_final,
                response_schema_value=response_schema_final,
                request_fields=request_fields,
                response_fields=response_fields
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
                "request_schema": request_schema_final,
                "response_schema": response_schema_final,
                "request_fields": request_fields,
                "request_header_fields": request_header_fields,
                "response_fields": response_fields,
                "contract_quality": quality,
                "header_desc": header_desc,
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
                "request_field_notes": field_note_seed(
                    item["request_fields"]
                ),
                "request_header_notes": field_note_seed(
                    item["request_header_fields"]
                ),
                "response_field_notes": field_note_seed(
                    item["response_fields"]
                ),
                "request_value_notes": {},
                "request_header_value_notes": {},
                "response_value_notes": {},
                "params_desc": item["params_desc"],
                "header_desc": item["header_desc"],
                "request_schema": item["request_schema"],
                "response_schema": item["response_schema"],
                "request_field_candidates": item["request_fields"],
                "request_header_candidates": item["request_header_fields"],
                "response_field_candidates": item["response_fields"],
                "contract_quality": item["contract_quality"],
                "contract_confidence": item["contract_quality"]["contract_confidence"],
                "confidence_reason": "; ".join(
                    item["contract_quality"]["reasons"]
                ),
                "request_example": item["request_example"],
                "response_example": item["response_example"],
                "response_demo": item["response_demo"],
                "usage_notes": item["usage_notes"]
            }
            for item in operations
        }
    }
    Path(output_file).parent.mkdir(
        parents=True,
        exist_ok=True
    )
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
