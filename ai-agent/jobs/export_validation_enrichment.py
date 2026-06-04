# -*- coding: utf-8 -*-

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import POSTGRES_CONFIG  # noqa: E402


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _load_response_example(response_body: str):
    try:
        return json.loads(response_body)
    except Exception:
        return response_body[:4000]


def _flatten_snapshot(
        snapshot: Any,
        prefix: str = "response"
) -> dict[str, str]:
    result = {}
    if isinstance(snapshot, dict):
        if snapshot.get("type") == "list":
            result[prefix] = "validated type: list"
            result.update(
                _flatten_snapshot(
                    snapshot.get("item_schema") or {},
                    f"{prefix}[]"
                )
            )
            return result
        if "type" in snapshot and len(snapshot) == 1:
            result[prefix] = f"validated type: {snapshot['type']}"
            return result
        for key, value in snapshot.items():
            child_prefix = (
                f"{prefix}.{key}"
                if prefix
                else key
            )
            result.update(
                _flatten_snapshot(
                    value,
                    child_prefix
                )
            )
    else:
        result[prefix] = f"validated type: {type(snapshot).__name__}"
    return result


def export_validation_enrichment(
        output_file: str,
        component_id: str = "",
        segment_id: str = "",
        limit: int = 200
):
    conn = psycopg2.connect(
        **POSTGRES_CONFIG
    )
    try:
        with conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            filters = [
                "avr.is_success = TRUE",
                "avr.api_identity_id IS NOT NULL"
            ]
            params: list[Any] = []
            if component_id:
                filters.append("UPPER(ai.component_id) = UPPER(%s)")
                params.append(component_id)
            if segment_id:
                filters.append("UPPER(ai.segment_id) = UPPER(%s)")
                params.append(segment_id)

            params.append(limit)
            cur.execute(
                f"""
                SELECT DISTINCT ON (avr.api_identity_id, avr.resolved_doc_version)
                    avr.id AS validation_id,
                    avr.test_env,
                    avr.response_status,
                    avr.response_body,
                    avr.response_schema_snapshot,
                    avr.validated_at,
                    avr.resolved_doc_version,
                    ai.component_id,
                    ai.segment_id,
                    ai.method,
                    ai.api_path,
                    ai.api_name
                FROM api_validation_record avr
                JOIN api_identity ai
                    ON ai.id = avr.api_identity_id
                WHERE {' AND '.join(filters)}
                ORDER BY
                    avr.api_identity_id,
                    avr.resolved_doc_version,
                    avr.validated_at DESC
                LIMIT %s
                """,
                params
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    operations = {}
    for row in rows:
        key = f"{row['method']} {row['api_path']}"
        snapshot = row.get("response_schema_snapshot") or {}
        operations[key] = {
            "api_name": row.get("api_name") or key,
            "response_example": _load_response_example(
                row.get("response_body") or ""
            ),
            "response_value_notes": _flatten_snapshot(
                snapshot
            ),
            "validation_notes": (
                f"Validated in {row.get('test_env')} "
                f"at {row.get('validated_at')} "
                f"with HTTP {row.get('response_status')}."
            ),
            "contract_confidence": 0.9,
            "confidence_reason": (
                "Response schema was observed from a real test environment. "
                "Review before merging into the official enrichment file."
            )
        }

    payload = {
        "source": "api_validation_record",
        "operation_count": len(operations),
        "operations": operations
    }
    output_path = Path(output_file)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    with open(
            output_path,
            "w",
            encoding="utf-8"
    ) as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
            default=_json_default
        )

    return payload


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Export successful API validation records as auditable enrichment "
            "suggestions."
        )
    )
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--component-id", default="")
    parser.add_argument("--segment-id", default="")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    payload = export_validation_enrichment(
        output_file=args.output_file,
        component_id=args.component_id,
        segment_id=args.segment_id,
        limit=args.limit
    )
    print(
        json.dumps(
            {
                "output_file": args.output_file,
                "operation_count": payload["operation_count"]
            },
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
