# -*- coding: utf-8 -*-

from dataclasses import dataclass


@dataclass
class BestPractice:

    id: int | None = None

    product_id: str = ""

    product_version: str = ""

    practice_name: str = ""

    scenario: str = ""

    description: str = ""

    recommended_component: str = ""

    recommended_api: str = ""

    sample_code: str = ""
