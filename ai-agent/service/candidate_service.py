# -*- coding: utf-8 -*-

from repository.candidate_repository import CandidateRepository
from service.knowledge_service import KnowledgeService
from models.candidate import KnowledgeCandidate

import logging

logger = logging.getLogger(__name__)


class CandidateService:

    def __init__(self, knowledge_service: KnowledgeService | None = None):

        self.repo = CandidateRepository()
        self.knowledge_service = knowledge_service or KnowledgeService()

    # =====================================
    # 提交候选知识
    # =====================================

    def submit_candidate(
            self,
            candidate_type,
            product_id,
            product_version,
            component_id,
            component_version,
            payload,
            created_by="AI_AGENT"
    ):

        candidate = KnowledgeCandidate(
            id=None,
            candidate_type=candidate_type,
            product_id=product_id,
            product_version=product_version,
            component_id=component_id,
            component_version=component_version,
            payload=payload,
            status="PENDING",
            created_by=created_by
        )

        candidate_id = self.repo.save(candidate)

        return (
            f"候选知识提交成功 ID={candidate_id}"
        )

    # =====================================
    # 查看待审核
    # =====================================

    def list_pending(self):

        candidates = self.repo.list_pending()

        if not candidates:

            return "暂无待审核知识"

        result = []

        for c in candidates:

            result.append(
                f"""
ID: {c.id}

类型:
{c.candidate_type}

产品:
{c.product_id}

版本:
{c.product_version}

组件:
{c.component_id}

内容:
{c.payload}
"""
            )

        return "\n".join(result)

    # =====================================
    # 审核通过
    # =====================================

    def approve(
            self,
            candidate_id
    ):

        candidate = (
            self.repo.find_by_id(
                candidate_id
            )
        )

        if not candidate:

            return "候选知识不存在"

        candidate_type = candidate.candidate_type
        payload = candidate.payload

        # ==================================
        # COMPONENT
        # ==================================

        if candidate_type == "COMPONENT":

            self.knowledge_service.add_component(
                product_id=candidate.product_id,
                product_version=candidate.product_version,
                comp_id=payload["comp_id"],
                comp_name=payload["comp_name"],
                comp_version=payload["comp_version"],
                description=payload["description"],
                scene=payload["scene"]
            )

        # ==================================
        # API
        # ==================================

        elif candidate_type == "API":

            self.knowledge_service.add_api(
                comp_id=candidate.component_id,
                comp_version=candidate.component_version,
                api_path=payload["api_path"],
                api_name=payload["api_name"],
                params_desc=payload["params_desc"],
                response_demo=payload["response_demo"],
                scene=payload["scene"]
            )

        else:

            return (
                f"未知候选类型: "
                f"{candidate_type}"
            )

        self.repo.approve(
            candidate_id
        )

        return (
            f"审核通过并已正式入库 "
            f"ID={candidate_id}"
        )

    # =====================================
    # 审核拒绝
    # =====================================

    def reject(
            self,
            candidate_id
    ):

        affected = self.repo.reject(
            candidate_id
        )

        return (
            f"审核拒绝 {affected} 条记录"
        )
