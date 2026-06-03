# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RequirementApiFeedback:
    product_id: str
    product_version: str
    requirement_text: str
    component_id: str
    component_version: str
    api_path: str
    api_name: str = ""
    feedback_type: str = "HUMAN_CONFIRM"
    feedback_reason: str = ""
    status: str = "PENDING"
    created_by: str = "AI_AGENT"
    id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_version": self.product_version,
            "requirement_text": self.requirement_text,
            "component_id": self.component_id,
            "component_version": self.component_version,
            "api_path": self.api_path,
            "api_name": self.api_name,
            "feedback_type": self.feedback_type,
            "feedback_reason": self.feedback_reason,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            )
        }
