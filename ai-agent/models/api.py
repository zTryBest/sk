# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class ApiInfo:
    """
    API信息
    """

    comp_id: str
    comp_version: str

    api_path: str
    api_name: str

    params_desc: str
    response_demo: str

    scene: str = ""
    request_method: str = ""
    capability_tags: list[str] = None
    request_schema: dict[str, Any] = None
    response_schema: dict[str, Any] = None
    request_headers: dict[str, Any] = None
    request_example: dict[str, Any] = None
    usage_notes: str = ""
    source_doc: str = ""
    version_status: str = "ACTIVE"
    validation_status: str = "UNKNOWN"
    latest_response_status: int | None = None
    latest_response_body: str = ""
    last_verified_at: datetime | None = None

    id: Optional[int] = None

    def __post_init__(self):
        if self.capability_tags is None:
            self.capability_tags = []

        if self.request_schema is None:
            self.request_schema = {}

        if self.response_schema is None:
            self.response_schema = {}

        if self.request_headers is None:
            self.request_headers = {}

        if self.request_example is None:
            self.request_example = {}

    def to_dict(self):
        return {
            "id": self.id,
            "comp_id": self.comp_id,
            "comp_version": self.comp_version,
            "api_path": self.api_path,
            "api_name": self.api_name,
            "params_desc": self.params_desc,
            "response_demo": self.response_demo,
            "scene": self.scene,
            "request_method": self.request_method,
            "capability_tags": self.capability_tags,
            "request_schema": self.request_schema,
            "response_schema": self.response_schema,
            "request_headers": self.request_headers,
            "request_example": self.request_example,
            "usage_notes": self.usage_notes,
            "source_doc": self.source_doc,
            "version_status": self.version_status,
            "validation_status": self.validation_status,
            "latest_response_status": self.latest_response_status,
            "latest_response_body": self.latest_response_body,
            "last_verified_at": (
                self.last_verified_at.isoformat()
                if self.last_verified_at
                else None
            )
        }
