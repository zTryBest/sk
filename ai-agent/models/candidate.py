# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Optional


@dataclass
class KnowledgeCandidate:
    """
    待审核知识
    """

    candidate_type: str

    product_id: str
    product_version: str

    component_id: str = ""
    component_version: str = ""

    payload: dict = None

    status: str = "PENDING"

    created_by: str = "AI_AGENT"

    id: Optional[int] = None

    def __post_init__(self):
        if self.payload is None:
            self.payload = {}
