# -*- coding: utf-8 -*-

import json
import logging
from typing import List, Optional

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from config.config import POSTGRES_CONFIG
from models.api import ApiInfo


logger = logging.getLogger(__name__)


class ApiRepository:

    def __init__(self):

        logger.info("初始化 ApiRepository")

        self.conn = psycopg2.connect(
            **POSTGRES_CONFIG
        )

    # =====================================
    # 领域对象转换
    # =====================================

    @staticmethod
    def _to_api_info(row) -> ApiInfo:
        """将数据库行转换为 ApiInfo 领域对象"""
        return ApiInfo(
            id=row["id"],
            comp_id=row["comp_id"],
            comp_version=row["comp_version"],
            api_path=row["api_path"],
            api_name=row["api_name"],
            params_desc=row["params_desc"],
            response_demo=row["response_demo"],
            scene=row["scene"],
            request_method=row.get("request_method", ""),
            capability_tags=row.get("capability_tags") or [],
            request_schema=row.get("request_schema") or {},
            response_schema=row.get("response_schema") or {},
            request_headers=row.get("request_headers") or {},
            request_example=row.get("request_example") or {},
            usage_notes=row.get("usage_notes", ""),
            source_doc=row.get("source_doc", ""),
            version_status=row.get("version_status", "ACTIVE"),
            validation_status=row.get("validation_status", "UNKNOWN"),
            latest_response_status=row.get("latest_response_status"),
            latest_response_body=row.get("latest_response_body", ""),
            last_verified_at=row.get("last_verified_at")
        )

    @staticmethod
    def _from_api_info(api_info: ApiInfo) -> tuple:
        """从 ApiInfo 领域对象提取数据库参数元组"""
        return (
            api_info.comp_id,
            api_info.comp_version,
            api_info.api_path,
            api_info.api_name,
            api_info.params_desc,
            api_info.response_demo,
            api_info.scene,
            api_info.request_method,
            api_info.capability_tags,
            Json(api_info.request_schema),
            Json(api_info.response_schema),
            Json(api_info.request_headers),
            Json(api_info.request_example),
            api_info.usage_notes,
            api_info.source_doc,
            api_info.version_status,
            api_info.validation_status,
            api_info.latest_response_status,
            api_info.latest_response_body,
            api_info.last_verified_at
        )

    # =====================================
    # 新增接口
    # =====================================

    def save(self, api_info: ApiInfo) -> int:
        """保存 API 信息到数据库"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO api_info
                (
                    comp_id,
                    comp_version,
                    api_path,
                    api_name,
                    params_desc,
                    response_demo,
                    scene,
                    request_method,
                    capability_tags,
                    request_schema,
                    response_schema,
                    request_headers,
                    request_example,
                    usage_notes,
                    source_doc,
                    version_status,
                    validation_status,
                    latest_response_status,
                    latest_response_body,
                    last_verified_at,
                    content
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                RETURNING id
                """,
                (
                    *self._from_api_info(api_info),
                    self._build_content(api_info)
                )
            )

            db_id = cur.fetchone()[0]

        self.conn.commit()

        return db_id

    @staticmethod
    def _build_content(api_info: ApiInfo) -> str:
        """构建向量化的文本内容"""
        return (
            f"接口名称:{api_info.api_name} "
            f"接口路径:{api_info.api_path} "
            f"请求方法:{api_info.request_method} "
            f"能力标签:{','.join(api_info.capability_tags)} "
            f"参数说明:{api_info.params_desc} "
            f"请求结构:{json.dumps(api_info.request_schema, ensure_ascii=False)} "
            f"响应结构:{json.dumps(api_info.response_schema, ensure_ascii=False)} "
            f"请求示例:{json.dumps(api_info.request_example, ensure_ascii=False)} "
            f"适用场景:{api_info.scene} "
            f"使用说明:{api_info.usage_notes} "
            f"响应示例:{api_info.response_demo}"
        )

    # =====================================
    # 根据ID查询单个
    # =====================================

    def find_by_id(self, api_id: int) -> Optional[ApiInfo]:
        """根据 ID 查询单个 API"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                "SELECT * FROM api_info WHERE id=%s",
                (api_id,)
            )

            row = cur.fetchone()

            if row is None:
                return None

            return self._to_api_info(row)

    def find_by_key(
            self,
            comp_id: str,
            comp_version: str,
            api_path: str
    ) -> Optional[ApiInfo]:
        """根据组件版本和接口路径查询单个 API"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM api_info
                WHERE comp_id=%s
                AND comp_version=%s
                AND api_path=%s
                """,
                (
                    comp_id,
                    comp_version,
                    api_path
                )
            )

            row = cur.fetchone()

            if row is None:
                return None

            return self._to_api_info(row)

    # =====================================
    # 根据ID批量查询
    # =====================================

    def find_by_ids(
            self,
            ids: List[int],
            comp_id: str,
            comp_version: str,
            limit: int = 5
    ) -> List[ApiInfo]:
        """根据 ID 列表批量查询 API"""
        sql = """
        SELECT *
        FROM api_info
        WHERE id = ANY(%s)
        AND comp_id=%s
        AND comp_version=%s
        LIMIT %s
        """

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                sql,
                (
                    ids,
                    comp_id,
                    comp_version,
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_api_info(row) for row in rows]

    def find_by_ids_in_components(
            self,
            ids: List[int],
            components: list[tuple[str, str]],
            limit: int = 5
    ) -> List[ApiInfo]:
        """根据 ID 列表，在指定组件版本范围内查询 API"""
        if not ids or not components:
            return []

        component_placeholders = ",".join(
            ["(%s,%s)"] * len(components)
        )

        sql = f"""
        SELECT *
        FROM api_info
        WHERE id = ANY(%s)
        AND (comp_id, comp_version) IN (
            VALUES {component_placeholders}
        )
        LIMIT %s
        """

        component_params = []
        for comp_id, comp_version in components:
            component_params.extend([comp_id, comp_version])

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                sql,
                (
                    ids,
                    *component_params,
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_api_info(row) for row in rows]

    # =====================================
    # 更新接口
    # =====================================

    def update(
            self,
            api_path: str,
            comp_id: str,
            comp_version: str,
            params_desc: Optional[str] = None,
            response_demo: Optional[str] = None,
            scene: Optional[str] = None
    ) -> int:
        """更新接口信息"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                UPDATE api_info
                SET
                    params_desc =
                        COALESCE(%s, params_desc),

                    response_demo =
                        COALESCE(%s, response_demo),

                    scene =
                        COALESCE(%s, scene),

                    updated_at = NOW()

                WHERE api_path=%s
                AND comp_id=%s
                AND comp_version=%s
                """,
                (
                    params_desc,
                    response_demo,
                    scene,
                    api_path,
                    comp_id,
                    comp_version
                )
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected

    def update_api_info(self, api_info: ApiInfo) -> int:
        """使用领域对象更新接口信息"""
        return self.update(
            api_path=api_info.api_path,
            comp_id=api_info.comp_id,
            comp_version=api_info.comp_version,
            params_desc=api_info.params_desc,
            response_demo=api_info.response_demo,
            scene=api_info.scene
        )

    def update_validation_result(
            self,
            api_id: int,
            validation_status: str,
            latest_response_status: int | None,
            latest_response_body: str
    ) -> int:
        """更新 API 最近一次真实环境验证结果"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                UPDATE api_info
                SET
                    validation_status=%s,
                    latest_response_status=%s,
                    latest_response_body=%s,
                    last_verified_at=NOW(),
                    updated_at=NOW()
                WHERE id=%s
                """,
                (
                    validation_status,
                    latest_response_status,
                    latest_response_body,
                    api_id
                )
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected

    # =====================================
    # 删除接口
    # =====================================

    def delete(
            self,
            api_path: str,
            comp_id: str,
            comp_version: str
    ) -> int:
        """删除接口"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                DELETE
                FROM api_info
                WHERE api_path=%s
                AND comp_id=%s
                AND comp_version=%s
                """,
                (
                    api_path,
                    comp_id,
                    comp_version
                )
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected

    # =====================================
    # 查询组件下所有接口
    # =====================================

    def list_apis(
            self,
            comp_id: str,
            comp_version: str
    ) -> List[ApiInfo]:
        """查询组件下的所有 API"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM api_info
                WHERE comp_id=%s
                AND comp_version=%s
                ORDER BY api_name
                """,
                (
                    comp_id,
                    comp_version
                )
            )

            rows = cur.fetchall()

            return [self._to_api_info(row) for row in rows]

    def list_apis_by_components(
            self,
            components: list[tuple[str, str]],
            limit: int = 200
    ) -> List[ApiInfo]:
        """查询多个组件版本下的 API"""
        if not components:
            return []

        component_placeholders = ",".join(
            ["(%s,%s)"] * len(components)
        )

        sql = f"""
        SELECT *
        FROM api_info
        WHERE (comp_id, comp_version) IN (
            VALUES {component_placeholders}
        )
        ORDER BY comp_id, comp_version, api_name
        LIMIT %s
        """

        component_params = []
        for comp_id, comp_version in components:
            component_params.extend([comp_id, comp_version])

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                sql,
                (
                    *component_params,
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_api_info(row) for row in rows]

    def search_by_keyword_in_components(
            self,
            keyword: str,
            components: list[tuple[str, str]],
            limit: int = 5
    ) -> List[ApiInfo]:
        """在组件范围内做关键词兜底检索"""
        if not keyword or not components:
            return []

        component_placeholders = ",".join(
            ["(%s,%s)"] * len(components)
        )

        sql = f"""
        SELECT *
        FROM api_info
        WHERE (comp_id, comp_version) IN (
            VALUES {component_placeholders}
        )
        AND (
            api_name ILIKE %s
            OR api_path ILIKE %s
            OR params_desc ILIKE %s
            OR scene ILIKE %s
            OR usage_notes ILIKE %s
            OR content ILIKE %s
        )
        LIMIT %s
        """

        component_params = []
        for comp_id, comp_version in components:
            component_params.extend([comp_id, comp_version])

        keyword_param = f"%{keyword}%"

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                sql,
                (
                    *component_params,
                    keyword_param,
                    keyword_param,
                    keyword_param,
                    keyword_param,
                    keyword_param,
                    keyword_param,
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_api_info(row) for row in rows]

    def list_validation_targets(
            self,
            limit: int = 50
    ) -> List[ApiInfo]:
        """查询需要做真实环境验证的 API"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM api_info
                WHERE version_status='ACTIVE'
                AND COALESCE(api_path, '') <> ''
                ORDER BY
                    last_verified_at NULLS FIRST,
                    id
                LIMIT %s
                """,
                (limit,)
            )

            rows = cur.fetchall()

            return [self._to_api_info(row) for row in rows]

    def list_validation_targets_with_context(
            self,
            limit: int = 50
    ) -> list[dict]:
        """查询需要做真实环境验证的 API，并带上平台版本上下文"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT
                    a.*,
                    c.product_id,
                    c.product_version,
                    c.comp_name
                FROM api_info a
                JOIN component_info c
                    ON c.comp_id = a.comp_id
                    AND c.comp_version = a.comp_version
                WHERE a.version_status='ACTIVE'
                AND COALESCE(a.api_path, '') <> ''
                ORDER BY
                    a.last_verified_at NULLS FIRST,
                    a.id
                LIMIT %s
                """,
                (limit,)
            )

            rows = cur.fetchall()

            return [
                {
                    "product_id": row["product_id"],
                    "product_version": row["product_version"],
                    "component_name": row["comp_name"],
                    "api": self._to_api_info(row)
                }
                for row in rows
            ]
