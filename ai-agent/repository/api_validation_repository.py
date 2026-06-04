# -*- coding: utf-8 -*-

import logging

import psycopg2
from psycopg2.extras import Json

from config.config import POSTGRES_CONFIG
from models.api_validation import ApiValidationRecord


logger = logging.getLogger(__name__)


class ApiValidationRepository:

    def __init__(self):
        logger.info("初始化 ApiValidationRepository")

        self.conn = psycopg2.connect(
            **POSTGRES_CONFIG
        )

    def save(self, record: ApiValidationRecord) -> int:
        with self.conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO api_validation_record
                (
                    api_id,
                    product_id,
                    product_version,
                    component_id,
                    segment_id,
                    component_version,
                    test_env,
                    request_url,
                    request_method,
                    request_headers,
                    request_body,
                    response_status,
                    response_body,
                    response_schema_snapshot,
                    is_success,
                    error_message,
                    api_identity_id,
                    api_contract_id,
                    resolved_component_version,
                    resolved_doc_version
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                RETURNING id
                """,
                (
                    record.api_id,
                    record.product_id,
                    record.product_version,
                    record.component_id,
                    record.segment_id,
                    record.component_version,
                    record.test_env,
                    record.request_url,
                    record.request_method,
                    Json(record.request_headers),
                    Json(record.request_body),
                    record.response_status,
                    record.response_body,
                    Json(record.response_schema_snapshot),
                    record.is_success,
                    record.error_message,
                    record.api_identity_id,
                    record.api_contract_id,
                    record.resolved_component_version,
                    record.resolved_doc_version
                )
            )

            record_id = cur.fetchone()[0]

        self.conn.commit()

        return record_id
