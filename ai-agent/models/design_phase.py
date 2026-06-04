# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ComponentCatalog:
    component_id: str
    component_name: str
    description: str = ""
    scene: str = ""
    id: int | None = None

    def to_dict(self):
        return self.__dict__


@dataclass
class ComponentSegment:
    component_id: str
    segment_id: str
    segment_name: str
    description: str = ""
    scene: str = ""
    id: int | None = None

    def to_dict(self):
        return self.__dict__


@dataclass
class ProductComponentBaseline:
    product_id: str
    product_version: str
    component_id: str
    component_version: str
    source: str = "BASELINE"
    id: int | None = None

    def to_dict(self):
        return self.__dict__


@dataclass
class ComponentDocVersion:
    component_id: str
    doc_version: str
    segment_id: str = ""
    doc_url: str = ""
    crawl_status: str = "PENDING"
    id: int | None = None

    def to_dict(self):
        return self.__dict__


@dataclass
class ApiIdentity:
    component_id: str
    method: str
    api_path: str
    api_name: str
    capability_tags: list[str]
    segment_id: str = ""
    scene: str = ""
    description: str = ""
    id: int | None = None

    def to_dict(self):
        return self.__dict__


@dataclass
class ApiContract:
    api_identity_id: int
    doc_version: str
    params_desc: str = ""
    request_schema: dict[str, Any] = None
    response_schema: dict[str, Any] = None
    request_headers: dict[str, Any] = None
    request_example: dict[str, Any] = None
    response_example: dict[str, Any] = None
    response_demo: str = ""
    usage_notes: str = ""
    source_url: str = ""
    id: int | None = None

    def __post_init__(self):
        if self.request_schema is None:
            self.request_schema = {}
        if self.response_schema is None:
            self.response_schema = {}
        if self.request_headers is None:
            self.request_headers = {}
        if self.request_example is None:
            self.request_example = {}
        if self.response_example is None:
            self.response_example = {}

    def to_dict(self):
        return self.__dict__


@dataclass
class ResolvedApiContract:
    api_identity: ApiIdentity
    api_contract: ApiContract | None
    requested_component_version: str
    resolved_doc_version: str | None
    match_level: str
    confidence: float
    risk: str
    lifecycle_status: str = "UNKNOWN"
    component_source: str = "BASELINE"

    def to_dict(self):
        return {
            "api_identity": self.api_identity.to_dict(),
            "api_contract": (
                self.api_contract.to_dict()
                if self.api_contract
                else None
            ),
            "requested_component_version": self.requested_component_version,
            "resolved_doc_version": self.resolved_doc_version,
            "match_level": self.match_level,
            "confidence": self.confidence,
            "risk": self.risk,
            "lifecycle_status": self.lifecycle_status,
            "component_source": self.component_source
        }
