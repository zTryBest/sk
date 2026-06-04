# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import POSTGRES_CONFIG  # noqa: E402
from utils.identifier_utils import normalize_identifier  # noqa: E402


CURRENT_VECTOR_FILES = [
    "faiss_data/api_identity.index",
    "faiss_data/api_identity_mapping.json",
]

LEGACY_VECTOR_FILES = [
    "faiss_data/api.index",
    "faiss_data/api_mapping.json",
    "faiss_data/component.index",
    "faiss_data/component_mapping.json",
]


class CleanupPlanner:

    def __init__(self):
        self.conn = psycopg2.connect(
            **POSTGRES_CONFIG
        )
        self.conn.autocommit = False

    def close(self):
        self.conn.close()

    def table_exists(
            self,
            table_name: str
    ) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
                """,
                (table_name,)
            )
            return bool(cur.fetchone()[0])

    def column_exists(
            self,
            table_name: str,
            column_name: str
    ) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND column_name = %s
                )
                """,
                (
                    table_name,
                    column_name
                )
            )
            return bool(cur.fetchone()[0])

    def fetch_scalar(
            self,
            sql: str,
            params: tuple = ()
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                params
            )
            return int(cur.fetchone()[0])

    def execute(
            self,
            sql: str,
            params: tuple = ()
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                params
            )
            return cur.rowcount

    def fetch_ids(
            self,
            sql: str,
            params: tuple = ()
    ) -> list[int]:
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                params
            )
            return [
                row[0]
                for row in cur.fetchall()
            ]

    def fetch_rows(
            self,
            sql: str,
            params: tuple = ()
    ) -> list[dict[str, Any]]:
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                sql,
                params
            )
            return [
                dict(row)
                for row in cur.fetchall()
            ]

    @staticmethod
    def _component_where(
            component_column: str,
            segment_column: str | None,
            component_id: str,
            segment_id: str | None
    ) -> tuple[str, list[str]]:
        clauses = [
            f"UPPER({component_column}) = %s"
        ]
        params = [
            component_id
        ]

        if segment_column and segment_id is not None:
            clauses.append(
                f"UPPER({segment_column}) = %s"
            )
            params.append(
                segment_id
            )

        return " AND ".join(clauses), params

    def _api_identity_ids(
            self,
            component_id: str | None,
            segment_id: str | None
    ) -> list[int]:
        if not self.table_exists("api_identity"):
            return []

        clauses = []
        params = []

        if component_id:
            clauses.append("UPPER(component_id) = %s")
            params.append(component_id)

        if (
                segment_id is not None
                and self.column_exists("api_identity", "segment_id")
        ):
            clauses.append("UPPER(segment_id) = %s")
            params.append(segment_id)

        where_sql = (
            "WHERE " + " AND ".join(clauses)
            if clauses
            else ""
        )
        return self.fetch_ids(
            f"""
            SELECT id
            FROM api_identity
            {where_sql}
            """,
            tuple(params)
        )

    def summarize_target(
            self,
            component_id: str | None,
            segment_id: str | None,
            product_id: str | None,
            product_version: str | None,
            include_legacy: bool,
            include_baseline: bool,
            include_component_metadata: bool
    ) -> list[dict[str, Any]]:
        actions = []
        identity_ids = self._api_identity_ids(
            component_id,
            segment_id
        )

        def add(
                table: str,
                count_sql: str,
                params: tuple,
                delete_sql: str
        ):
            if self.table_exists(table):
                actions.append({
                    "table": table,
                    "count": self.fetch_scalar(
                        count_sql,
                        params
                    ),
                    "delete_sql": delete_sql,
                    "params": params
                })

        if identity_ids:
            id_params = (identity_ids,)
            add(
                "api_contract",
                """
                SELECT COUNT(*)
                FROM api_contract
                WHERE api_identity_id = ANY(%s)
                """,
                id_params,
                "-- cascades from api_identity"
            )
            add(
                "api_lifecycle",
                """
                SELECT COUNT(*)
                FROM api_lifecycle
                WHERE api_identity_id = ANY(%s)
                """,
                id_params,
                "-- cascades from api_identity"
            )
            add(
                "api_identity",
                """
                SELECT COUNT(*)
                FROM api_identity
                WHERE id = ANY(%s)
                """,
                id_params,
                """
                DELETE FROM api_identity
                WHERE id = ANY(%s)
                """
            )

        for table in [
            "api_validation_record",
            "requirement_api_feedback",
        ]:
            if not self.table_exists(table):
                continue

            clauses = []
            params = []

            if (
                    identity_ids
                    and self.column_exists(table, "api_identity_id")
            ):
                clauses.append("api_identity_id = ANY(%s)")
                params.append(identity_ids)

            if component_id and self.column_exists(table, "component_id"):
                component_clauses = [
                    "UPPER(component_id) = %s"
                ]
                component_params = [
                    component_id
                ]
                if (
                        segment_id is not None
                        and self.column_exists(table, "segment_id")
                ):
                    component_clauses.append("UPPER(segment_id) = %s")
                    component_params.append(segment_id)
                clauses.append(
                    "(" + " AND ".join(component_clauses) + ")"
                )
                params.extend(component_params)

            if clauses:
                where_sql = " OR ".join(clauses)
                add(
                    table,
                    f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE {where_sql}
                    """,
                    tuple(params),
                    f"""
                    DELETE FROM {table}
                    WHERE {where_sql}
                    """
                )

        if component_id:
            if self.table_exists("component_doc_version"):
                has_segment = self.column_exists(
                    "component_doc_version",
                    "segment_id"
                )
                where_sql, params = self._component_where(
                    "component_id",
                    "segment_id" if has_segment else None,
                    component_id,
                    segment_id
                )
                add(
                    "component_doc_version",
                    f"""
                    SELECT COUNT(*)
                    FROM component_doc_version
                    WHERE {where_sql}
                    """,
                    tuple(params),
                    f"""
                    DELETE FROM component_doc_version
                    WHERE {where_sql}
                    """
                )

            if self.table_exists("component_version_doc_mapping"):
                has_segment = self.column_exists(
                    "component_version_doc_mapping",
                    "segment_id"
                )
                where_sql, params = self._component_where(
                    "component_id",
                    "segment_id" if has_segment else None,
                    component_id,
                    segment_id
                )
                add(
                    "component_version_doc_mapping",
                    f"""
                    SELECT COUNT(*)
                    FROM component_version_doc_mapping
                    WHERE {where_sql}
                    """,
                    tuple(params),
                    f"""
                    DELETE FROM component_version_doc_mapping
                    WHERE {where_sql}
                    """
                )

            if include_baseline and self.table_exists("product_component_baseline"):
                clauses = [
                    "UPPER(component_id) = %s"
                ]
                params = [
                    component_id
                ]
                if product_id:
                    clauses.append("UPPER(product_id) = %s")
                    params.append(product_id)
                if product_version:
                    clauses.append("product_version = %s")
                    params.append(product_version)
                where_sql = " AND ".join(clauses)
                add(
                    "product_component_baseline",
                    f"""
                    SELECT COUNT(*)
                    FROM product_component_baseline
                    WHERE {where_sql}
                    """,
                    tuple(params),
                    f"""
                    DELETE FROM product_component_baseline
                    WHERE {where_sql}
                    """
                )

            if include_component_metadata and self.table_exists("component_segment"):
                has_segment = self.column_exists(
                    "component_segment",
                    "segment_id"
                )
                where_sql, params = self._component_where(
                    "component_id",
                    "segment_id" if has_segment else None,
                    component_id,
                    segment_id
                )
                add(
                    "component_segment",
                    f"""
                    SELECT COUNT(*)
                    FROM component_segment
                    WHERE {where_sql}
                    """,
                    tuple(params),
                    f"""
                    DELETE FROM component_segment
                    WHERE {where_sql}
                    """
                )

            if include_component_metadata and self.table_exists("component_catalog"):
                add(
                    "component_catalog",
                    """
                    SELECT COUNT(*)
                    FROM component_catalog
                    WHERE UPPER(component_id) = %s
                    """,
                    (component_id,),
                    """
                    DELETE FROM component_catalog
                    WHERE UPPER(component_id) = %s
                    """
                )

            if include_legacy:
                if self.table_exists("api_info"):
                    add(
                        "api_info",
                        """
                        SELECT COUNT(*)
                        FROM api_info
                        WHERE UPPER(comp_id) = %s
                        """,
                        (component_id,),
                        """
                        DELETE FROM api_info
                        WHERE UPPER(comp_id) = %s
                        """
                    )

                if self.table_exists("component_info"):
                    clauses = [
                        "UPPER(comp_id) = %s"
                    ]
                    params = [
                        component_id
                    ]
                    if product_id:
                        clauses.append("UPPER(product_id) = %s")
                        params.append(product_id)
                    if product_version:
                        clauses.append("product_version = %s")
                        params.append(product_version)
                    where_sql = " AND ".join(clauses)
                    add(
                        "component_info",
                        f"""
                        SELECT COUNT(*)
                        FROM component_info
                        WHERE {where_sql}
                        """,
                        tuple(params),
                        f"""
                        DELETE FROM component_info
                        WHERE {where_sql}
                        """
                    )

        return actions

    def summarize_all_design(self) -> list[dict[str, Any]]:
        tables = [
            "api_validation_record",
            "requirement_api_feedback",
            "api_lifecycle",
            "api_contract",
            "api_identity",
            "component_version_doc_mapping",
            "component_doc_version",
            "component_segment",
            "product_component_baseline",
            "component_catalog",
            "product_release",
        ]
        return self._truncate_actions(tables)

    def summarize_all(self) -> list[dict[str, Any]]:
        tables = [
            "api_validation_record",
            "requirement_api_feedback",
            "api_lifecycle",
            "api_contract",
            "api_identity",
            "component_version_doc_mapping",
            "component_doc_version",
            "component_segment",
            "product_component_baseline",
            "component_catalog",
            "product_release",
            "api_info",
            "component_info",
            "best_practice",
            "knowledge_candidate",
        ]
        return self._truncate_actions(tables)

    def _truncate_actions(
            self,
            tables: list[str]
    ) -> list[dict[str, Any]]:
        actions = []
        existing_tables = [
            table
            for table in tables
            if self.table_exists(table)
        ]
        truncate_sql = (
            "TRUNCATE TABLE "
            + ", ".join(existing_tables)
            + " RESTART IDENTITY CASCADE"
            if existing_tables
            else ""
        )

        for table in existing_tables:
            actions.append({
                "table": table,
                "count": self.fetch_scalar(
                    f"SELECT COUNT(*) FROM {table}"
                ),
                "delete_sql": truncate_sql,
                "params": (),
                "truncate_group": True
            })

        return actions

    def execute_actions(
            self,
            actions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        executed = []
        truncate_sql = next(
            (
                action["delete_sql"]
                for action in actions
                if action.get("truncate_group")
            ),
            None
        )

        if truncate_sql:
            self.execute(truncate_sql)
            self.conn.commit()
            return [
                {
                    "table": action["table"],
                    "deleted_or_truncated": action["count"]
                }
                for action in actions
            ]

        for action in actions:
            if action["delete_sql"].strip().startswith("--"):
                executed.append({
                    "table": action["table"],
                    "deleted_or_truncated": "cascade",
                    "counted": action["count"]
                })
                continue

            deleted = self.execute(
                action["delete_sql"],
                action["params"]
            )
            executed.append({
                "table": action["table"],
                "deleted_or_truncated": deleted
            })

        self.conn.commit()
        return executed


def _remove_vector_files(
        files: list[str],
        confirm: bool
) -> list[dict[str, Any]]:
    result = []
    for file_name in files:
        path = project_root / file_name
        exists = path.exists()
        item = {
            "file": str(path),
            "exists": exists,
            "removed": False
        }
        if confirm and exists:
            path.unlink()
            item["removed"] = True
        result.append(item)
    return result


def _rebuild_current_vector_index():
    from jobs.rebuild_vector_indexes import rebuild_api_identity_index

    rebuild_api_identity_index()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Clean dirty Swagger-imported knowledge data and related FAISS indexes. "
            "Dry-run by default; add --confirm to delete."
        )
    )
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument(
        "--component-id",
        help="Clean one component, for example AAA."
    )
    scope.add_argument(
        "--all-design",
        action="store_true",
        help="Clean all design-phase API identity/contract/baseline data."
    )
    scope.add_argument(
        "--all",
        action="store_true",
        help="Clean all knowledge data, including legacy component_info/api_info."
    )
    scope.add_argument(
        "--vector-only",
        action="store_true",
        help="Only clean vector files, do not touch database."
    )

    parser.add_argument("--segment-id", default=None)
    parser.add_argument("--product-id", default=None)
    parser.add_argument("--product-version", default=None)
    parser.add_argument(
        "--include-baseline",
        action="store_true",
        help="Also delete matching product_component_baseline rows."
    )
    parser.add_argument(
        "--include-component-metadata",
        action="store_true",
        help="Also delete component_catalog/component_segment metadata."
    )
    parser.add_argument(
        "--include-legacy",
        action="store_true",
        help="Also delete matching legacy api_info/component_info rows."
    )
    parser.add_argument(
        "--delete-legacy-vector-files",
        action="store_true",
        help="Delete legacy faiss_data/api.index and component.index files."
    )
    parser.add_argument(
        "--delete-current-vector-files",
        action="store_true",
        help="Delete current api_identity vector files instead of rebuilding them."
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild current api_identity FAISS index after database cleanup."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete data. Without this flag the script only reports counts."
    )

    args = parser.parse_args()

    component_id = normalize_identifier(args.component_id)
    segment_id = (
        normalize_identifier(args.segment_id)
        if args.segment_id is not None
        else None
    )
    product_id = (
        normalize_identifier(args.product_id)
        if args.product_id
        else None
    )

    report: dict[str, Any] = {
        "mode": "EXECUTE" if args.confirm else "DRY_RUN",
        "database": {
            "host": POSTGRES_CONFIG.get("host"),
            "port": POSTGRES_CONFIG.get("port"),
            "database": POSTGRES_CONFIG.get("database"),
            "user": POSTGRES_CONFIG.get("user"),
        },
        "target": {
            "component_id": component_id,
            "segment_id": segment_id,
            "product_id": product_id,
            "product_version": args.product_version,
        },
        "actions": [],
        "executed": [],
        "vector_files": [],
        "vector_rebuilt": False,
        "message": ""
    }

    if args.vector_only:
        vector_files = list(CURRENT_VECTOR_FILES)
        if args.delete_legacy_vector_files:
            vector_files.extend(LEGACY_VECTOR_FILES)
        report["vector_files"] = _remove_vector_files(
            vector_files,
            confirm=args.confirm
        )
        report["message"] = (
            "vector-only cleanup completed"
            if args.confirm
            else "dry-run only; add --confirm to remove vector files"
        )
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2
            )
        )
        return

    planner = CleanupPlanner()
    try:
        if args.all:
            actions = planner.summarize_all()
        elif args.all_design:
            actions = planner.summarize_all_design()
        else:
            actions = planner.summarize_target(
                component_id=component_id,
                segment_id=segment_id,
                product_id=product_id,
                product_version=args.product_version,
                include_legacy=args.include_legacy,
                include_baseline=args.include_baseline,
                include_component_metadata=args.include_component_metadata
            )

        report["actions"] = [
            {
                "table": action["table"],
                "count": action["count"]
            }
            for action in actions
        ]

        if args.confirm:
            report["executed"] = planner.execute_actions(actions)
        else:
            planner.conn.rollback()

    finally:
        planner.close()

    vector_files_to_remove = []
    if args.delete_current_vector_files:
        vector_files_to_remove.extend(CURRENT_VECTOR_FILES)
    if args.delete_legacy_vector_files:
        vector_files_to_remove.extend(LEGACY_VECTOR_FILES)

    if vector_files_to_remove:
        report["vector_files"] = _remove_vector_files(
            vector_files_to_remove,
            confirm=args.confirm
        )

    if args.rebuild_index and args.confirm:
        _rebuild_current_vector_index()
        report["vector_rebuilt"] = True

    if args.rebuild_index and not args.confirm:
        report["message"] = (
            "dry-run only; add --confirm to delete rows and rebuild vector index"
        )
    elif not args.confirm:
        report["message"] = "dry-run only; add --confirm to execute cleanup"
    else:
        report["message"] = "cleanup completed"

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
