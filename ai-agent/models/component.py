# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Optional


@dataclass
class ComponentInfo:
    """
    组件信息
    """

    product_id: str
    product_version: str

    comp_id: str
    comp_name: str
    comp_version: str

    description: str
    scene: str = ""

    id: Optional[int] = None

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_version": self.product_version,
            "comp_id": self.comp_id,
            "comp_name": self.comp_name,
            "comp_version": self.comp_version,
            "description": self.description,
            "scene": self.scene
        }
