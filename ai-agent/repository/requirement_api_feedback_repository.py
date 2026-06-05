# -*- coding: utf-8 -*-

import logging
from typing import List, Optional

from psycopg2.extras import RealDictCursor

from models.requirement_api_feedback import RequirementApiFeedback
from repository.postgres_connection import ResilientPostgresConnection


logger = logging.getLogger(__name__)


class RequirementApiFeedbackRepository:

    def __init__(self):
        logger.info("初始化 RequirementApiFeedbackRepository")

        self.conn = ResilientPostgresConnection(
            name=self.__class__.__name__
        )

    @staticmethod
    def _to_feedback(row) -> RequirementApiFeedback:
        return RequirementApiFeedback(
            id=row["id"],
            product_id=row["product_id"],
            product_version=row["product_version"],
            requirement_text=row["requirement_text"],
            component_id=row["component_id"],
            component_version=row["component_version"],
            api_path=row["api_path"],
            api_name=row["api_name"],
            feedback_type=row["feedback_type"],
            feedback_reason=row["feedback_reason"],
            status=row["status"],
            created_by=row["created_by"],
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    @staticmethod
    def _build_content(feedback: RequirementApiFeedback) -> str:
        return (
            f"需求:{feedback.requirement_text} "
            f"组件:{feedback.component_id} "
            f"组件版本:{feedback.component_version} "
            f"接口名称:{feedback.api_name} "
            f"接口路径:{feedback.api_path} "
            f"反馈类型:{feedback.feedback_type} "
            f"确认原因:{feedback.feedback_reason}"
        )

    def save(self, feedback: RequirementApiFeedback) -> int:
        with self.conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO requirement_api_feedback
                (
                    product_id,
                    product_version,
                    requirement_text,
                    component_id,
                    component_version,
                    api_path,
                    api_name,
                    feedback_type,
                    feedback_reason,
                    status,
                    created_by,
                    content
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                RETURNING id
                """,
                (
                    feedback.product_id,
                    feedback.product_version,
                    feedback.requirement_text,
                    feedback.component_id,
                    feedback.component_version,
                    feedback.api_path,
                    feedback.api_name,
                    feedback.feedback_type,
                    feedback.feedback_reason,
                    feedback.status,
                    feedback.created_by,
                    self._build_content(feedback)
                )
            )

            feedback_id = cur.fetchone()[0]

        self.conn.commit()

        return feedback_id

    def find_by_id(
            self,
            feedback_id: int
    ) -> Optional[RequirementApiFeedback]:
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM requirement_api_feedback
                WHERE id=%s
                """,
                (feedback_id,)
            )

            row = cur.fetchone()

            if row is None:
                return None

            return self._to_feedback(row)

    def list_pending(self) -> List[RequirementApiFeedback]:
        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM requirement_api_feedback
                WHERE status='PENDING'
                ORDER BY id DESC
                """
            )

            rows = cur.fetchall()

            return [self._to_feedback(row) for row in rows]

    def approve(
            self,
            feedback_id: int
    ) -> int:
        with self.conn.cursor() as cur:

            cur.execute(
                """
                UPDATE requirement_api_feedback
                SET
                    status='APPROVED',
                    updated_at=NOW()
                WHERE id=%s
                """,
                (feedback_id,)
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected

    def reject(
            self,
            feedback_id: int
    ) -> int:
        with self.conn.cursor() as cur:

            cur.execute(
                """
                UPDATE requirement_api_feedback
                SET
                    status='REJECTED',
                    updated_at=NOW()
                WHERE id=%s
                """,
                (feedback_id,)
            )

            affected = cur.rowcount

        self.conn.commit()

        return affected

    def find_approved_by_ids(
            self,
            ids: List[int],
            product_id: str,
            product_version: str,
            limit: int = 5
    ) -> List[RequirementApiFeedback]:
        if not ids:
            return []

        with self.conn.cursor(
                cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT *
                FROM requirement_api_feedback
                WHERE id = ANY(%s)
                AND product_id=%s
                AND product_version=%s
                AND status='APPROVED'
                LIMIT %s
                """,
                (
                    ids,
                    product_id,
                    product_version,
                    limit
                )
            )

            rows = cur.fetchall()

            return [self._to_feedback(row) for row in rows]
