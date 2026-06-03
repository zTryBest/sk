# -*- coding: utf-8 -*-

from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from config.config import POSTGRES_CONFIG
from models.best_practice import BestPractice

import logging

logger = logging.getLogger(__name__)


class BestPracticeRepository:

    def __init__(self):

        logger.info("初始化 BestPracticeRepository")

        self.conn = psycopg2.connect(
            **POSTGRES_CONFIG
        )

    # =====================================
    # 领域对象转换
    # =====================================

    @staticmethod
    def _to_best_practice(row) -> BestPractice:
        """将数据库行转换为 BestPractice 领域对象"""
        return BestPractice(
            id=row["id"],
            product_id=row["product_id"],
            product_version=row["product_version"],
            practice_name=row["practice_name"],
            scenario=row["scenario"],
            description=row["description"],
            recommended_component=row["recommended_component"],
            recommended_api=row["recommended_api"],
            sample_code=row["sample_code"]
        )

    @staticmethod
    def _from_best_practice(practice: BestPractice) -> tuple:
        """从 BestPractice 领域对象提取数据库参数元组"""
        return (
            practice.product_id,
            practice.product_version,
            practice.practice_name,
            practice.scenario,
            practice.description,
            practice.recommended_component,
            practice.recommended_api,
            practice.sample_code
        )

    @staticmethod
    def _build_content(practice: BestPractice) -> str:
        """构建向量化的文本内容"""
        return (
            f"实践名称:{practice.practice_name} "
            f"适用场景:{practice.scenario} "
            f"方案说明:{practice.description} "
            f"推荐组件:{practice.recommended_component} "
            f"推荐接口:{practice.recommended_api}"
        )

    # =====================================
    # 新增最佳实践
    # =====================================

    def save(self, practice: BestPractice) -> int:
        """保存最佳实践到数据库"""
        content = self._build_content(practice)

        with self.conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO best_practice
                (
                    product_id,
                    product_version,
                    practice_name,
                    scenario,
                    description,
                    recommended_component,
                    recommended_api,
                    sample_code,
                    content
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                RETURNING id
                """,
                (
                    *self._from_best_practice(practice),
                    content
                )
            )

            practice_id = cur.fetchone()[0]

        self.conn.commit()

        return practice_id

    # =====================================
    # 根据ID查询单个
    # =====================================

    def find_by_id(self, practice_id: int) -> Optional[BestPractice]:
        """根据 ID 查询单个最佳实践"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                "SELECT * FROM best_practice WHERE id=%s",
                (practice_id,)
            )

            row = cur.fetchone()

            if row is None:
                return None

            return self._to_best_practice(row)

    # =====================================
    # 根据ID批量查询
    # =====================================

    def find_by_ids(
            self,
            ids: List[int],
            limit: int = 5
    ) -> List[BestPractice]:
        """根据 ID 列表批量查询最佳实践"""
        sql = """
        SELECT *
        FROM best_practice
        WHERE id = ANY(%s)
        LIMIT %s
        """

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                sql,
                (
                    ids,
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_best_practice(row) for row in rows]

    # =====================================
    # 语义检索 - 关键词搜索（降级方案）
    # =====================================

    def search(
            self,
            keyword: str,
            limit: int = 10
    ) -> List[BestPractice]:
        """使用关键词搜索最佳实践（降级方案）"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM best_practice
                WHERE
                    scenario ILIKE %s
                    OR practice_name ILIKE %s
                    OR description ILIKE %s
                LIMIT %s
                """,
                (
                    f"%{keyword}%",
                    f"%{keyword}%",
                    f"%{keyword}%",
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_best_practice(row) for row in rows]
