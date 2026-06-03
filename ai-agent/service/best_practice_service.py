# -*- coding: utf-8 -*-

from service.knowledge_service import KnowledgeService


class BestPracticeService:

    def __init__(self, knowledge_service: KnowledgeService | None = None):
        self.knowledge_service = knowledge_service or KnowledgeService()

    def add_practice(
            self,
            product_id,
            product_version,
            practice_name,
            scenario,
            description,
            recommended_component,
            recommended_api,
            sample_code=""
    ):

        return self.knowledge_service.add_practice(
            product_id=product_id,
            product_version=product_version,
            practice_name=practice_name,
            scenario=scenario,
            description=description,
            recommended_component=recommended_component,
            recommended_api=recommended_api,
            sample_code=sample_code
        )

    def search_practice(
            self,
            keyword
    ):

        return self.knowledge_service.query_practice(
            query=keyword
        )
