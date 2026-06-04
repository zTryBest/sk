# -*- coding: utf-8 -*-

import hashlib
import json
import logging

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from config.config import POSTGRES_CONFIG
from models.design_phase import (
    ApiContract,
    ApiIdentity,
    ComponentCatalog,
    ComponentDocVersion,
    ComponentSegment,
    ProductComponentBaseline,
)
from utils.identifier_utils import normalize_identifier


logger = logging.getLogger(__name__)


class DesignRepository:

    def __init__(self):
        logger.info("初始化 DesignRepository")
        self.conn = psycopg2.connect(
            **POSTGRES_CONFIG
        )

    @staticmethod
    def _api_identity_content(api: ApiIdentity) -> str:
        return (
            f"组件:{api.component_id} "
            f"组件段:{api.segment_id or 'default'} "
            f"接口名称:{api.api_name} "
            f"方法:{api.method} "
            f"路径:{api.api_path} "
            f"能力标签:{','.join(api.capability_tags or [])} "
            f"场景:{api.scene} "
            f"描述:{api.description}"
        )

    @staticmethod
    def _component_content(component: ComponentCatalog) -> str:
        return (
            f"组件:{component.component_id} "
            f"组件名称:{component.component_name} "
            f"描述:{component.description} "
            f"场景:{component.scene}"
        )

    @staticmethod
    def _segment_content(segment: ComponentSegment) -> str:
        return (
            f"组件:{segment.component_id} "
            f"组件段:{segment.segment_id} "
            f"组件段名称:{segment.segment_name} "
            f"描述:{segment.description} "
            f"场景:{segment.scene}"
        )

    @staticmethod
    def _contract_hash(contract: ApiContract) -> str:
        payload = {
            "params_desc": contract.params_desc,
            "request_schema": contract.request_schema,
            "response_schema": contract.response_schema,
            "request_headers": contract.request_headers,
            "request_example": contract.request_example,
            "response_example": contract.response_example,
            "response_demo": contract.response_demo,
            "usage_notes": contract.usage_notes,
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()

    def upsert_product_release(
            self,
            product_id: str,
            product_version: str,
            product_name: str = "",
            description: str = ""
    ) -> int:
        product_id = normalize_identifier(product_id)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO product_release
                (
                    product_id,
                    product_version,
                    product_name,
                    description
                )
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (product_id, product_version)
                DO UPDATE SET
                    product_name=EXCLUDED.product_name,
                    description=EXCLUDED.description,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    product_id,
                    product_version,
                    product_name,
                    description
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def upsert_component(
            self,
            component: ComponentCatalog
    ) -> int:
        component.component_id = normalize_identifier(
            component.component_id
        )
        content = self._component_content(
            component
        )
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO component_catalog
                (
                    component_id,
                    component_name,
                    description,
                    scene,
                    content
                )
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (component_id)
                DO UPDATE SET
                    component_name=EXCLUDED.component_name,
                    description=EXCLUDED.description,
                    scene=EXCLUDED.scene,
                    content=EXCLUDED.content,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    component.component_id,
                    component.component_name,
                    component.description,
                    component.scene,
                    content
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def upsert_component_segment(
            self,
            segment: ComponentSegment
    ) -> int:
        segment.component_id = normalize_identifier(
            segment.component_id
        )
        segment.segment_id = normalize_identifier(
            segment.segment_id
        )
        content = self._segment_content(
            segment
        )
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO component_segment
                (
                    component_id,
                    segment_id,
                    segment_name,
                    description,
                    scene,
                    content
                )
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (component_id, segment_id)
                DO UPDATE SET
                    segment_name=EXCLUDED.segment_name,
                    description=EXCLUDED.description,
                    scene=EXCLUDED.scene,
                    content=EXCLUDED.content,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    segment.component_id,
                    segment.segment_id,
                    segment.segment_name,
                    segment.description,
                    segment.scene,
                    content
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def upsert_product_component_baseline(
            self,
            baseline: ProductComponentBaseline
    ) -> int:
        baseline.product_id = normalize_identifier(
            baseline.product_id
        )
        baseline.component_id = normalize_identifier(
            baseline.component_id
        )
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO product_component_baseline
                (
                    product_id,
                    product_version,
                    component_id,
                    component_version,
                    source
                )
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (product_id, product_version, component_id)
                DO UPDATE SET
                    component_version=EXCLUDED.component_version,
                    source=EXCLUDED.source,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    baseline.product_id,
                    baseline.product_version,
                    baseline.component_id,
                    baseline.component_version,
                    baseline.source
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def upsert_component_doc_version(
            self,
            doc: ComponentDocVersion
    ) -> int:
        doc.component_id = normalize_identifier(
            doc.component_id
        )
        doc.segment_id = normalize_identifier(
            doc.segment_id
        )
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO component_doc_version
                (
                    component_id,
                    segment_id,
                    doc_version,
                    doc_url,
                    crawl_status
                )
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (component_id, segment_id, doc_version)
                DO UPDATE SET
                    doc_url=EXCLUDED.doc_url,
                    crawl_status=EXCLUDED.crawl_status,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    doc.component_id,
                    doc.segment_id or "",
                    doc.doc_version,
                    doc.doc_url,
                    doc.crawl_status
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def upsert_component_version_doc_mapping(
            self,
            component_id: str,
            component_version: str,
            doc_version: str,
            segment_id: str = "",
            mapping_type: str = "MANUAL",
            confidence: float = 1.0,
            reason: str = "",
            created_by: str = "AI_AGENT"
    ) -> int:
        component_id = normalize_identifier(component_id)
        segment_id = normalize_identifier(segment_id)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO component_version_doc_mapping
                (
                    component_id,
                    segment_id,
                    component_version,
                    doc_version,
                    mapping_type,
                    confidence,
                    reason,
                    created_by
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (component_id, segment_id, component_version)
                DO UPDATE SET
                    doc_version=EXCLUDED.doc_version,
                    mapping_type=EXCLUDED.mapping_type,
                    confidence=EXCLUDED.confidence,
                    reason=EXCLUDED.reason,
                    created_by=EXCLUDED.created_by,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    component_id,
                    segment_id or "",
                    component_version,
                    doc_version,
                    mapping_type,
                    confidence,
                    reason,
                    created_by
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def upsert_api_identity(
            self,
            api: ApiIdentity
    ) -> int:
        api.component_id = normalize_identifier(
            api.component_id
        )
        api.segment_id = normalize_identifier(
            api.segment_id
        )
        method = api.method.upper()
        content = self._api_identity_content(
            api
        )
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_identity
                (
                    component_id,
                    segment_id,
                    method,
                    api_path,
                    api_name,
                    capability_tags,
                    scene,
                    description,
                    content
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (component_id, segment_id, method, api_path)
                DO UPDATE SET
                    api_name=EXCLUDED.api_name,
                    capability_tags=EXCLUDED.capability_tags,
                    scene=EXCLUDED.scene,
                    description=EXCLUDED.description,
                    content=EXCLUDED.content,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    api.component_id,
                    api.segment_id or "",
                    method,
                    api.api_path,
                    api.api_name,
                    api.capability_tags,
                    api.scene,
                    api.description,
                    content
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def upsert_api_contract(
            self,
            contract: ApiContract
    ) -> int:
        content_hash = self._contract_hash(
            contract
        )
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_contract
                (
                    api_identity_id,
                    doc_version,
                    params_desc,
                    request_schema,
                    response_schema,
                    request_headers,
                    request_example,
                    response_example,
                    response_demo,
                    usage_notes,
                    source_url,
                    content_hash
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (api_identity_id, doc_version)
                DO UPDATE SET
                    params_desc=EXCLUDED.params_desc,
                    request_schema=EXCLUDED.request_schema,
                    response_schema=EXCLUDED.response_schema,
                    request_headers=EXCLUDED.request_headers,
                    request_example=EXCLUDED.request_example,
                    response_example=EXCLUDED.response_example,
                    response_demo=EXCLUDED.response_demo,
                    usage_notes=EXCLUDED.usage_notes,
                    source_url=EXCLUDED.source_url,
                    content_hash=EXCLUDED.content_hash,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    contract.api_identity_id,
                    contract.doc_version,
                    contract.params_desc,
                    Json(contract.request_schema),
                    Json(contract.response_schema),
                    Json(contract.request_headers),
                    Json(contract.request_example),
                    Json(contract.response_example),
                    contract.response_demo,
                    contract.usage_notes,
                    contract.source_url,
                    content_hash
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def upsert_api_lifecycle(
            self,
            api_identity_id: int,
            doc_version: str,
            status: str = "PRESENT",
            change_type: str = "UNCHANGED"
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_lifecycle
                (
                    api_identity_id,
                    doc_version,
                    status,
                    change_type
                )
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (api_identity_id, doc_version)
                DO UPDATE SET
                    status=EXCLUDED.status,
                    change_type=EXCLUDED.change_type,
                    updated_at=NOW()
                RETURNING id
                """,
                (
                    api_identity_id,
                    doc_version,
                    status,
                    change_type
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id

    def list_products(self):
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT *
                FROM product_release
                ORDER BY product_id, product_version
                """
            )
            return cur.fetchall()

    def list_product_components(
            self,
            product_id: str,
            product_version: str
    ):
        product_id = normalize_identifier(product_id)
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    b.*,
                    c.component_name,
                    c.description,
                    c.scene
                FROM product_component_baseline b
                LEFT JOIN component_catalog c
                    ON UPPER(c.component_id) = UPPER(b.component_id)
                WHERE UPPER(b.product_id)=%s
                AND b.product_version=%s
                ORDER BY b.component_id
                """,
                (
                    product_id,
                    product_version
                )
            )
            return cur.fetchall()

    def list_component_segments(
            self,
            component_id: str
    ):
        component_id = normalize_identifier(component_id)
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT *
                FROM component_segment
                WHERE UPPER(component_id)=%s
                ORDER BY segment_id
                """,
                (component_id,)
            )
            return cur.fetchall()

    def list_component_doc_versions(
            self,
            component_id: str,
            segment_id: str | None = ""
    ) -> list[str]:
        component_id = normalize_identifier(component_id)
        if segment_id is not None:
            segment_id = normalize_identifier(segment_id)
        with self.conn.cursor() as cur:
            if segment_id is None:
                cur.execute(
                    """
                    SELECT DISTINCT doc_version
                    FROM component_doc_version
                    WHERE UPPER(component_id)=%s
                    ORDER BY doc_version
                    """,
                    (component_id,)
                )
            else:
                cur.execute(
                    """
                    SELECT doc_version
                    FROM component_doc_version
                    WHERE UPPER(component_id)=%s
                    AND UPPER(segment_id)=%s
                    ORDER BY doc_version
                    """,
                    (
                        component_id,
                        segment_id or ""
                    )
                )
            return [
                row[0]
                for row in cur.fetchall()
            ]

    def list_component_doc_version_rows(
            self,
            component_id: str,
            segment_id: str | None = None
    ):
        component_id = normalize_identifier(component_id)
        if segment_id is not None:
            segment_id = normalize_identifier(segment_id)
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            if segment_id is None:
                cur.execute(
                    """
                    SELECT *
                    FROM component_doc_version
                    WHERE UPPER(component_id)=%s
                    ORDER BY segment_id, doc_version
                    """,
                    (component_id,)
                )
            else:
                cur.execute(
                    """
                    SELECT *
                    FROM component_doc_version
                    WHERE UPPER(component_id)=%s
                    AND UPPER(segment_id)=%s
                    ORDER BY doc_version
                    """,
                    (
                        component_id,
                        segment_id or ""
                    )
                )
            return cur.fetchall()

    def get_component_doc_mapping(
            self,
            component_id: str,
            component_version: str,
            segment_id: str = ""
    ):
        component_id = normalize_identifier(component_id)
        segment_id = normalize_identifier(segment_id)
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT *
                FROM component_version_doc_mapping
                WHERE UPPER(component_id)=%s
                AND UPPER(segment_id)=%s
                AND component_version=%s
                """,
                (
                    component_id,
                    segment_id or "",
                    component_version
                )
            )
            return cur.fetchone()

    @staticmethod
    def _to_api_identity(row) -> ApiIdentity:
        return ApiIdentity(
            id=row["id"],
            component_id=row["component_id"],
            segment_id=row.get("segment_id", ""),
            method=row["method"],
            api_path=row["api_path"],
            api_name=row["api_name"],
            capability_tags=row.get("capability_tags") or [],
            scene=row.get("scene", ""),
            description=row.get("description", "")
        )

    @staticmethod
    def _to_api_contract(row) -> ApiContract:
        return ApiContract(
            id=row["id"],
            api_identity_id=row["api_identity_id"],
            doc_version=row["doc_version"],
            params_desc=row["params_desc"],
            request_schema=row["request_schema"] or {},
            response_schema=row["response_schema"] or {},
            request_headers=row["request_headers"] or {},
            request_example=row["request_example"] or {},
            response_example=row["response_example"] or {},
            response_demo=row["response_demo"],
            usage_notes=row["usage_notes"],
            source_url=row["source_url"]
        )

    def find_api_identity_by_key(
            self,
            component_id: str,
            method: str,
            api_path: str,
            segment_id: str | None = ""
    ):
        component_id = normalize_identifier(component_id)
        if segment_id is not None:
            segment_id = normalize_identifier(segment_id)
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            if segment_id is None:
                cur.execute(
                    """
                    SELECT *
                    FROM api_identity
                    WHERE UPPER(component_id)=%s
                    AND method=%s
                    AND api_path=%s
                    ORDER BY segment_id
                    LIMIT 1
                    """,
                    (
                        component_id,
                        method.upper(),
                        api_path
                    )
                )
            else:
                cur.execute(
                    """
                    SELECT *
                    FROM api_identity
                    WHERE UPPER(component_id)=%s
                    AND UPPER(segment_id)=%s
                    AND method=%s
                    AND api_path=%s
                    """,
                    (
                        component_id,
                        segment_id or "",
                        method.upper(),
                        api_path
                    )
                )
            row = cur.fetchone()
        return (
            self._to_api_identity(row)
            if row
            else None
        )

    def find_api_identities_by_ids(
            self,
            ids: list[int],
            component_ids: list[str],
            limit: int = 5
    ) -> list[ApiIdentity]:
        if not ids or not component_ids:
            return []
        component_ids = [
            normalize_identifier(component_id)
            for component_id in component_ids
        ]

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT *
                FROM api_identity
                WHERE id = ANY(%s)
                AND UPPER(component_id) = ANY(%s)
                LIMIT %s
                """,
                (
                    ids,
                    component_ids,
                    limit
                )
            )
            rows = cur.fetchall()
        return [
            self._to_api_identity(row)
            for row in rows
        ]

    def search_api_identities_by_keyword(
            self,
            keyword: str,
            component_ids: list[str],
            limit: int = 5
    ) -> list[ApiIdentity]:
        if not keyword or not component_ids:
            return []
        component_ids = [
            normalize_identifier(component_id)
            for component_id in component_ids
        ]

        keyword_param = f"%{keyword}%"

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT *
                FROM api_identity
                WHERE UPPER(component_id) = ANY(%s)
                AND (
                    api_name ILIKE %s
                    OR api_path ILIKE %s
                    OR scene ILIKE %s
                    OR description ILIKE %s
                    OR content ILIKE %s
                )
                LIMIT %s
                """,
                (
                    component_ids,
                    keyword_param,
                    keyword_param,
                    keyword_param,
                    keyword_param,
                    keyword_param,
                    limit
                )
            )
            rows = cur.fetchall()
        return [
            self._to_api_identity(row)
            for row in rows
        ]

    def get_api_contract(
            self,
            api_identity_id: int,
            doc_version: str
    ):
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT *
                FROM api_contract
                WHERE api_identity_id=%s
                AND doc_version=%s
                """,
                (
                    api_identity_id,
                    doc_version
                )
            )
            row = cur.fetchone()
        return (
            self._to_api_contract(row)
            if row
            else None
        )

    def list_api_contract_versions(
            self,
            api_identity_id: int
    ) -> list[str]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT doc_version
                FROM api_contract
                WHERE api_identity_id=%s
                ORDER BY doc_version
                """,
                (api_identity_id,)
            )
            return [
                row[0]
                for row in cur.fetchall()
            ]

    def get_api_lifecycle_status(
            self,
            api_identity_id: int,
            doc_version: str
    ) -> str:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM api_lifecycle
                WHERE api_identity_id=%s
                AND doc_version=%s
                """,
                (
                    api_identity_id,
                    doc_version
                )
            )
            row = cur.fetchone()

        return (
            row[0]
            if row
            else "UNKNOWN"
        )

    def list_api_identity_ids(self) -> list[int]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM api_identity
                ORDER BY id
                """
            )
            return [
                row[0]
                for row in cur.fetchall()
            ]

    def get_api_identity_by_id(
            self,
            api_identity_id: int
    ):
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT *
                FROM api_identity
                WHERE id=%s
                """,
                (api_identity_id,)
            )
            row = cur.fetchone()

        return (
            self._to_api_identity(row)
            if row
            else None
        )

    def list_api_identities_for_component(
            self,
            component_id: str,
            segment_id: str | None = None
    ) -> list[ApiIdentity]:
        component_id = normalize_identifier(component_id)
        if segment_id is not None:
            segment_id = normalize_identifier(segment_id)
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            if segment_id is None:
                cur.execute(
                    """
                    SELECT *
                    FROM api_identity
                    WHERE UPPER(component_id)=%s
                    ORDER BY segment_id, method, api_path
                    """,
                    (component_id,)
                )
            else:
                cur.execute(
                    """
                    SELECT *
                    FROM api_identity
                    WHERE UPPER(component_id)=%s
                    AND UPPER(segment_id)=%s
                    ORDER BY method, api_path
                    """,
                    (
                        component_id,
                        segment_id or ""
                    )
                )
            rows = cur.fetchall()

        return [
            self._to_api_identity(row)
            for row in rows
        ]

    def get_latest_contract_before(
            self,
            api_identity_id: int,
            doc_version: str
    ) -> ApiContract | None:
        from utils.version_utils import compare_version_parts, parse_version

        requested = parse_version(doc_version)
        candidates = []

        for version in self.list_api_contract_versions(api_identity_id):
            parsed = parse_version(version)
            if not parsed.parts:
                continue

            if (
                    requested.major is not None
                    and parsed.major != requested.major
            ):
                continue

            if compare_version_parts(parsed.parts, requested.parts) < 0:
                candidates.append(
                    (
                        version,
                        parsed.parts
                    )
                )

        if not candidates:
            return None

        selected_version = max(
            candidates,
            key=lambda item: item[1]
        )[0]

        return self.get_api_contract(
            api_identity_id=api_identity_id,
            doc_version=selected_version
        )

    def list_contract_validation_targets(
            self,
            limit: int = 50
    ) -> list[dict]:
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    ai.id AS identity_id,
                    ai.component_id,
                    ai.segment_id,
                    ai.method,
                    ai.api_path,
                    ai.api_name,
                    ai.capability_tags,
                    ai.scene,
                    ai.description,
                    ac.id AS contract_id,
                    ac.doc_version,
                    ac.request_schema,
                    ac.response_schema,
                    ac.request_headers,
                    ac.request_example
                FROM api_identity ai
                JOIN api_contract ac
                    ON ac.api_identity_id = ai.id
                ORDER BY ac.id
                LIMIT %s
                """,
                (limit,)
            )
            rows = cur.fetchall()

        result = []
        for row in rows:
            result.append({
                "identity": ApiIdentity(
                    id=row["identity_id"],
                    component_id=row["component_id"],
                    segment_id=row.get("segment_id", ""),
                    method=row["method"],
                    api_path=row["api_path"],
                    api_name=row["api_name"],
                    capability_tags=row.get("capability_tags") or [],
                    scene=row.get("scene", ""),
                    description=row.get("description", "")
                ),
                "contract": ApiContract(
                    id=row["contract_id"],
                    api_identity_id=row["identity_id"],
                    doc_version=row["doc_version"],
                    request_schema=row.get("request_schema") or {},
                    response_schema=row.get("response_schema") or {},
                    request_headers=row.get("request_headers") or {},
                    request_example=row.get("request_example") or {}
                )
            })

        return result
