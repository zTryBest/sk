# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class ApiValidationRecord:
    api_id: int | None
    product_id: str
    product_version: str
    component_id: str
    component_version: str
    test_env: str
    request_url: str
    request_method: str
    request_headers: dict[str, Any]
    request_body: dict[str, Any]
    response_status: int | None = None
    response_body: str = ""
    response_schema_snapshot: dict[str, Any] = None
    is_success: bool = False
    error_message: str = ""
    id: Optional[int] = None
    validated_at: datetime | None = None
    api_identity_id: int | None = None
    api_contract_id: int | None = None
    resolved_component_version: str = ""
    resolved_doc_version: str = ""

    def __post_init__(self):
        if self.response_schema_snapshot is None:
            self.response_schema_snapshot = {}

    def to_dict(self):
        return {
            "id": self.id,
            "api_id": self.api_id,
            "product_id": self.product_id,
            "product_version": self.product_version,
            "component_id": self.component_id,
            "component_version": self.component_version,
            "test_env": self.test_env,
            "request_url": self.request_url,
            "request_method": self.request_method,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "response_body": self.response_body,
            "response_schema_snapshot": self.response_schema_snapshot,
            "is_success": self.is_success,
            "error_message": self.error_message,
            "validated_at": (
                self.validated_at.isoformat()
                if self.validated_at
                else None
            ),
            "api_identity_id": self.api_identity_id,
            "api_contract_id": self.api_contract_id,
            "resolved_component_version": self.resolved_component_version,
            "resolved_doc_version": self.resolved_doc_version
        }
