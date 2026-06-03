# -*- coding: utf-8 -*-

from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from config.config import POSTGRES_CONFIG
from models.candidate import KnowledgeCandidate

import logging
import json

logger = logging.getLogger(__name__)


class CandidateRepository:

    def __init__(self):

        logger.info("初始化 CandidateRepository")

        self.conn = psycopg2.connect(
            **POSTGRES_CONFIG
        )

    # =====================================
    # 领域对象转换
    # =====================================

    @staticmethod
    def _to_knowledge_candidate(row) -> KnowledgeCandidate:
        """将数据库行转换为 KnowledgeCandidate 领域对象"""
        return KnowledgeCandidate(
            id=row["id"],
            candidate_type=row["candidate_type"],
            product_id=row["product_id"],
            product_version=row["product_version"],
            component_id=row["component_id"],
            component_version=row["component_version"],
            payload=row.get("payload", {}),
            status=row["status"],
            created_by=row["created_by"]
        )

    @staticmethod
    def _from_knowledge_candidate(candidate: KnowledgeCandidate) -> tuple:
        """从 KnowledgeCandidate 领域对象提取数据库参数元组"""
        import json
        return (
            candidate.candidate_type,
            candidate.product_id,
            candidate.product_version,
            candidate.component_id,
            candidate.component_version,
            json.dumps(candidate.payload),
            candidate.created_by
        )

    # =====================================
    # 新增候选知识
    # =====================================

    def save(self, candidate: KnowledgeCandidate) -> int:
        """保存候选知识到数据库"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO knowledge_candidate
                (
                    candidate_type,
                    product_id,
                    product_version,
                    component_id,
                    component_version,
                    payload,
                    status,
                    created_by
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,'PENDING',%s
                )
                RETURNING id
                """,
                self._from_knowledge_candidate(candidate)
            )

            candidate_id = cur.fetchone()[0]

        self.conn.commit()

        return candidate_id

    # =====================================
    # 查询待审核知识
    # =====================================

    def list_pending(self) -> List[KnowledgeCandidate]:
        """查询所有待审核的候选知识"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM knowledge_candidate
                WHERE status='PENDING'
                ORDER BY id DESC
                """
            )

            rows = cur.fetchall()

            return [self._to_knowledge_candidate(row) for row in rows]

    # =====================================
    # 查询所有候选知识
    # =====================================

    def list_all(self) -> List[KnowledgeCandidate]:
        """查询所有候选知识"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM knowledge_candidate
                ORDER BY id DESC
                """
            )

            rows = cur.fetchall()

            return [self._to_knowledge_candidate(row) for row in rows]

    # =====================================
    # 查询单条
    # =====================================

    def find_by_id(
            self,
            candidate_id: int
    ) -> Optional[KnowledgeCandidate]:
        """根据 ID 查询单个候选知识"""
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM knowledge_candidate
                WHERE id=%s
                """,
                (
                    candidate_id,
                )
            )

            row = cur.fetchone()

            if row is None:
                return None

            return self._to_knowledge_candidate(row)

    # =====================================
    # 审核通过
    # =====================================

    def approve(
            self,
            candidate_id: int
    ) -> int:
        """审核通过候选知识"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                UPDATE knowledge_candidate
                SET status='APPROVED'
                WHERE id=%s
                """,
                (
                    candidate_id,
                )
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected

    # =====================================
    # 审核拒绝
    # =====================================

    def reject(
            self,
            candidate_id: int
    ) -> int:
        """审核拒绝候选知识"""
        with self.conn.cursor() as cur:

            cur.execute(
                """
                UPDATE knowledge_candidate
                SET status='REJECTED'
                WHERE id=%s
                """,
                (
                    candidate_id,
                )
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected
