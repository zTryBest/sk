# -*- coding: utf-8 -*-

from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from config.config import POSTGRES_CONFIG
from models.component import ComponentInfo

import logging

logger = logging.getLogger(__name__)


class ComponentRepository:

    def __init__(self):

        logger.info("初始化 ComponentRepository")

        self.conn = psycopg2.connect(
            **POSTGRES_CONFIG
        )

    # =====================================
    # 领域对象转换
    # =====================================

    @staticmethod
    def _to_component_info(row) -> ComponentInfo:
        """将数据库行转换为 ComponentInfo 领域对象"""
        return ComponentInfo(
            id=row["id"],
            product_id=row["product_id"],
            product_version=row["product_version"],
            comp_id=row["comp_id"],
            comp_name=row["comp_name"],
            comp_version=row["comp_version"],
            description=row["description"],
            scene=row["scene"]
        )

    @staticmethod
    def _from_component_info(comp_info: ComponentInfo) -> tuple:
        """从 ComponentInfo 领域对象提取数据库参数元组"""
        return (
            comp_info.product_id,
            comp_info.product_version,
            comp_info.comp_id,
            comp_info.comp_name,
            comp_info.comp_version,
            comp_info.description,
            comp_info.scene
        )

    # =====================================
    # 新增组件
    # =====================================

    def save(self, comp_info: ComponentInfo) -> int:
        """保存组件信息到数据库"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO component_info
                (
                    product_id,
                    product_version,
                    comp_id,
                    comp_name,
                    comp_version,
                    description,
                    scene,
                    content
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s
                )
                RETURNING id
                """,
                (
                    *self._from_component_info(comp_info),
                    self._build_content(comp_info)
                )
            )

            db_id = cur.fetchone()[0]

        self.conn.commit()

        return db_id

    @staticmethod
    def _build_content(comp_info: ComponentInfo) -> str:
        """构建向量化的文本内容"""
        return (
            f"组件名称:{comp_info.comp_name} "
            f"组件标识:{comp_info.comp_id} "
            f"组件版本:{comp_info.comp_version} "
            f"组件描述:{comp_info.description} "
            f"适用场景:{comp_info.scene}"
        )

    # =====================================
    # 根据ID查询单个
    # =====================================

    def find_by_id(self, comp_id: int) -> Optional[ComponentInfo]:
        """根据 ID 查询单个组件"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                "SELECT * FROM component_info WHERE id=%s",
                (comp_id,)
            )

            row = cur.fetchone()

            if row is None:
                return None

            return self._to_component_info(row)

    # =====================================
    # 根据ID批量查询
    # =====================================

    def find_by_ids(
            self,
            ids: List[int],
            product_id: str,
            product_version: str,
            limit: int = 5
    ) -> List[ComponentInfo]:
        """根据 ID 列表批量查询组件"""
        sql = """
        SELECT *
        FROM component_info
        WHERE id = ANY(%s)
        AND product_id=%s
        AND product_version=%s
        LIMIT %s
        """

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                sql,
                (
                    ids,
                    product_id,
                    product_version,
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_component_info(row) for row in rows]

    # =====================================
    # 更新组件
    # =====================================

    def update(
            self,
            comp_id: str,
            product_id: str,
            product_version: str,
            description: Optional[str] = None,
            scene: Optional[str] = None
    ) -> int:
        """更新组件信息"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                UPDATE component_info
                SET
                    description =
                        COALESCE(%s, description),

                    scene =
                        COALESCE(%s, scene)

                WHERE comp_id=%s
                AND product_id=%s
                AND product_version=%s
                """,
                (
                    description,
                    scene,
                    comp_id,
                    product_id,
                    product_version
                )
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected

    def update_component_info(self, comp_info: ComponentInfo) -> int:
        """使用领域对象更新组件信息"""
        return self.update(
            comp_id=comp_info.comp_id,
            product_id=comp_info.product_id,
            product_version=comp_info.product_version,
            description=comp_info.description,
            scene=comp_info.scene
        )

    # =====================================
    # 删除组件
    # =====================================

    def delete(
            self,
            comp_id: str,
            product_id: str,
            product_version: str
    ) -> int:
        """删除组件"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                DELETE
                FROM component_info
                WHERE comp_id=%s
                AND product_id=%s
                AND product_version=%s
                """,
                (
                    comp_id,
                    product_id,
                    product_version
                )
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected

    # =====================================
    # 产品列表
    # =====================================

    def list_products(self):
        """获取所有产品列表"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT DISTINCT
                    product_id,
                    product_version
                FROM component_info
                ORDER BY
                    product_id,
                    product_version
                """
            )

            return cur.fetchall()

    # =====================================
    # 组件列表
    # =====================================

    def list_components(
            self,
            product_id: str,
            product_version: str
    ) -> List[ComponentInfo]:
        """获取指定产品下的组件列表"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM component_info
                WHERE product_id=%s
                AND product_version=%s
                ORDER BY comp_name
                """,
                (
                    product_id,
                    product_version
                )
            )

            rows = cur.fetchall()

            return [self._to_component_info(row) for row in rows]

    def search_by_keyword(
            self,
            keyword: str,
            product_id: str,
            product_version: str,
            limit: int = 5
    ) -> List[ComponentInfo]:
        """在指定产品版本下做组件关键词兜底检索"""
        if not keyword:
            return []

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM component_info
                WHERE product_id=%s
                AND product_version=%s
                AND (
                    comp_id ILIKE %s
                    OR comp_name ILIKE %s
                    OR description ILIKE %s
                    OR scene ILIKE %s
                    OR content ILIKE %s
                )
                ORDER BY comp_name
                LIMIT %s
                """,
                (
                    product_id,
                    product_version,
                    f"%{keyword}%",
                    f"%{keyword}%",
                    f"%{keyword}%",
                    f"%{keyword}%",
                    f"%{keyword}%",
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_component_info(row) for row in rows]
