# -*- coding: utf-8 -*-

import logging
import re

from openai import OpenAI

from config.config import (
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    EMBEDDING_TIMEOUT,
    VECTOR_BACKEND,
)
from models.design_phase import (
    ApiContract,
    ApiIdentity,
    ResolvedApiContract,
)
from repository.design_repository import DesignRepository
from utils.identifier_utils import (
    normalize_identifier,
    normalize_identifier_map,
)
from utils.version_utils import find_nearest_doc_version
from vector.factory import create_vector_store


logger = logging.getLogger(__name__)


class KnowledgeService:

    def __init__(self):
        self.embedding_client = OpenAI(
            api_key=EMBEDDING_API_KEY,
            base_url=EMBEDDING_BASE_URL,
            timeout=EMBEDDING_TIMEOUT
        )

        self.design_repo = DesignRepository()

        self.api_identity_vector_store = create_vector_store(
            backend=VECTOR_BACKEND,
            index_file="faiss_data/api_identity.index",
            mapping_file="faiss_data/api_identity_mapping.json",
            dimension=EMBEDDING_DIM
        )

    def _get_embedding(
            self,
            text: str
    ):
        response = self.embedding_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )

        return [
            float(x)
            for x in response.data[0].embedding
        ]

    def list_products(self):
        products = self.design_repo.list_products()

        return {
            "products": [
                dict(product)
                for product in products
            ],
            "count": len(products)
        }

    def list_product_components(
            self,
            product_id: str,
            product_version: str,
            component_overrides: dict[str, str] | None = None
    ):
        product_id = normalize_identifier(product_id)
        component_overrides = normalize_identifier_map(
            component_overrides
        )
        components = self._resolve_product_components(
            product_id=product_id,
            product_version=product_version,
            component_overrides=component_overrides
        )

        return {
            "product_id": product_id,
            "product_version": product_version,
            "components": components,
            "count": len(components)
        }

    def _resolve_product_components(
            self,
            product_id: str,
            product_version: str,
            component_overrides: dict[str, str]
    ) -> list[dict]:
        product_id = normalize_identifier(product_id)
        component_overrides = normalize_identifier_map(
            component_overrides
        )
        baseline_rows = self.design_repo.list_product_components(
            product_id=product_id,
            product_version=product_version
        )

        components = []

        for row in baseline_rows:
            component_id = normalize_identifier(row["component_id"])
            component_version = row["component_version"]
            source = row.get("source", "BASELINE")

            if component_id in component_overrides:
                component_version = component_overrides[component_id]
                source = "USER_OVERRIDE"

            segments = [
                dict(segment)
                for segment in self.design_repo.list_component_segments(
                    component_id=component_id
                )
            ]

            components.append({
                "product_id": product_id,
                "product_version": product_version,
                "component_id": component_id,
                "component_name": row.get("component_name", ""),
                "component_version": component_version,
                "description": row.get("description", ""),
                "scene": row.get("scene", ""),
                "segments": segments,
                "source": source
            })

        for component_id, component_version in component_overrides.items():
            if any(
                    item["component_id"] == component_id
                    for item in components
            ):
                continue

            components.append({
                "product_id": product_id,
                "product_version": product_version,
                "component_id": component_id,
                "component_name": "",
                "component_version": component_version,
                "description": "",
                "scene": "",
                "segments": [
                    dict(segment)
                    for segment in self.design_repo.list_component_segments(
                        component_id=component_id
                    )
                ],
                "source": "USER_OVERRIDE_EXTRA"
            })

        return components

    def list_component_segments(
            self,
            component_id: str
    ):
        component_id = normalize_identifier(component_id)
        segments = self.design_repo.list_component_segments(
            component_id=component_id
        )

        return {
            "component_id": component_id,
            "segments": [
                dict(segment)
                for segment in segments
            ],
            "count": len(segments)
        }

    def list_component_doc_versions(
            self,
            component_id: str,
            segment_id: str | None = None
    ):
        component_id = normalize_identifier(component_id)
        if segment_id is not None:
            segment_id = normalize_identifier(segment_id)
        rows = self.design_repo.list_component_doc_version_rows(
            component_id=component_id,
            segment_id=segment_id
        )

        return {
            "component_id": component_id,
            "segment_id": segment_id,
            "doc_versions": [
                dict(row)
                for row in rows
            ],
            "count": len(rows)
        }

    def resolve_component_doc_version(
            self,
            component_id: str,
            component_version: str,
            segment_id: str = ""
    ):
        component_id = normalize_identifier(component_id)
        segment_id = normalize_identifier(segment_id)
        manual_mapping = self.design_repo.get_component_doc_mapping(
            component_id=component_id,
            component_version=component_version,
            segment_id=segment_id
        )

        if manual_mapping:
            return {
                "component_id": component_id,
                "segment_id": segment_id,
                "requested_component_version": component_version,
                "resolved_doc_version": manual_mapping["doc_version"],
                "match_level": manual_mapping["mapping_type"],
                "confidence": float(manual_mapping["confidence"]),
                "risk": manual_mapping["reason"],
                "source": "MANUAL_MAPPING"
            }

        doc_versions = self.design_repo.list_component_doc_versions(
            component_id=component_id,
            segment_id=segment_id
        )
        resolved = find_nearest_doc_version(
            component_version=component_version,
            doc_versions=doc_versions
        )

        return {
            "component_id": component_id,
            "segment_id": segment_id,
            "requested_component_version": component_version,
            "resolved_doc_version": resolved["doc_version"],
            "match_level": resolved["match_level"],
            "confidence": resolved["confidence"],
            "risk": resolved["risk"],
            "source": "AUTO_RESOLVE"
        }

    def submit_component_version_doc_mapping(
            self,
            component_id: str,
            component_version: str,
            doc_version: str,
            segment_id: str = "",
            reason: str = "",
            created_by: str = "AI_AGENT"
    ):
        component_id = normalize_identifier(component_id)
        segment_id = normalize_identifier(segment_id)
        mapping_id = self.design_repo.upsert_component_version_doc_mapping(
            component_id=component_id,
            component_version=component_version,
            doc_version=doc_version,
            segment_id=segment_id,
            mapping_type="MANUAL",
            confidence=1.0,
            reason=reason,
            created_by=created_by
        )

        return {
            "mapping_id": mapping_id,
            "message": "组件版本到接口文档版本的人工映射已保存"
        }

    @staticmethod
    def _extract_search_terms(text: str) -> list[str]:
        if not text:
            return []

        stopwords = {
            "需要",
            "支持",
            "实现",
            "进行",
            "根据",
            "接口",
            "功能",
            "字段",
            "信息",
            "数据",
            "返回",
            "请求",
        }
        terms = []
        normalized = text.lower()

        terms.extend(
            re.findall(
                r"[a-zA-Z][a-zA-Z0-9_./:-]{1,}|[0-9]+",
                normalized
            )
        )

        for chunk in re.findall(r"[\u4e00-\u9fff]+", text):
            if 2 <= len(chunk) <= 6:
                terms.append(chunk)
            for size in (2, 3, 4):
                if len(chunk) <= size:
                    continue
                for start in range(0, len(chunk) - size + 1):
                    terms.append(chunk[start:start + size])

        result = []
        seen = set()
        for term in terms:
            term = term.strip().lower()
            if len(term) < 2 or term in stopwords or term in seen:
                continue
            seen.add(term)
            result.append(term)
            if len(result) >= 40:
                break
        return result

    @staticmethod
    def _term_overlap_score(
            terms: list[str],
            content: str
    ) -> int:
        if not terms or not content:
            return 0
        content = content.lower()
        return sum(
            1
            for term in terms
            if term.lower() in content
        )

    def find_apis_for_requirement(
            self,
            product_id: str,
            product_version: str,
            requirement_item: str,
            component_overrides: dict[str, str] | None = None,
            limit: int = 5
    ):
        product_id = normalize_identifier(product_id)
        component_overrides = normalize_identifier_map(
            component_overrides
        )
        components = self._resolve_product_components(
            product_id=product_id,
            product_version=product_version,
            component_overrides=component_overrides
        )

        if not components:
            return {
                "product_id": product_id,
                "product_version": product_version,
                "requirement_item": requirement_item,
                "matched_apis": [],
                "missing_info": [
                    "当前平台版本没有组件基线数据，请先维护 product_component_baseline。"
                ]
            }

        component_versions = {
            item["component_id"]: item["component_version"]
            for item in components
        }
        component_sources = {
            item["component_id"]: item["source"]
            for item in components
        }
        component_ids = list(
            component_versions.keys()
        )
        search_terms = self._extract_search_terms(
            requirement_item
        )

        matched_apis = []
        missing_info = []

        if self.api_identity_vector_store.count() > 0:
            try:
                query_embedding = self._get_embedding(
                    requirement_item
                )
                candidates = self.api_identity_vector_store.search(
                    query_embedding,
                    top_k=100
                )
                candidate_ids = [
                    item["db_id"]
                    for item in candidates
                ]
                score_map = {
                    item["db_id"]: item["score"]
                    for item in candidates
                }
                identities = self.design_repo.find_api_identities_by_ids(
                    ids=candidate_ids,
                    component_ids=component_ids,
                    limit=max(limit * 5, 25)
                )

                vector_matches = []
                for identity in identities:
                    resolved = self._resolve_api_contract(
                        api_identity=identity,
                        component_version=component_versions[identity.component_id],
                        component_source=component_sources[identity.component_id]
                    )
                    search_content = self.design_repo.build_api_search_content(
                        identity,
                        resolved.api_contract
                    )
                    keyword_score = self._term_overlap_score(
                        search_terms,
                        search_content
                    )
                    vector_score = float(
                        score_map.get(identity.id) or 0
                    )
                    combined_score = vector_score + min(
                        keyword_score * 0.03,
                        0.3
                    )
                    item = resolved.to_dict()
                    item["score"] = combined_score
                    item["vector_score"] = vector_score
                    item["keyword_score"] = keyword_score
                    item["match_source"] = "HYBRID_VECTOR"
                    item["match_reason"] = "接口身份语义信息与需求分解项相似"
                    vector_matches.append(item)
                vector_matches.sort(
                    key=lambda item: item["score"],
                    reverse=True
                )
                matched_apis.extend(
                    vector_matches[:limit]
                )
            except Exception as e:
                missing_info.append(
                    f"语义检索不可用，已降级为关键词检索: {e}"
                )
        else:
            missing_info.append(
                "API身份向量索引为空，已降级为关键词检索。"
            )

        if len(matched_apis) < limit:
            keyword_identities = self.design_repo.search_api_identities_by_keywords(
                keywords=search_terms or [requirement_item],
                component_ids=component_ids,
                limit=max(limit * 3, 10)
            )
            existing_ids = {
                item["api_identity"]["id"]
                for item in matched_apis
            }

            for identity in keyword_identities:
                if identity.id in existing_ids:
                    continue

                resolved = self._resolve_api_contract(
                    api_identity=identity,
                    component_version=component_versions[identity.component_id],
                    component_source=component_sources[identity.component_id]
                )
                item = resolved.to_dict()
                item["score"] = None
                item["keyword_score"] = self._term_overlap_score(
                    search_terms,
                    self.design_repo.build_api_search_content(
                        identity,
                        resolved.api_contract
                    )
                )
                item["match_source"] = "KEYWORD"
                item["match_reason"] = "接口身份关键词信息与需求分解项匹配"
                matched_apis.append(item)

                if len(matched_apis) >= limit:
                    break

        if not matched_apis:
            missing_info.append(
                "未找到候选 API，请先导入接口文档或提交人工反馈。"
            )

        return {
            "product_id": product_id,
            "product_version": product_version,
            "requirement_item": requirement_item,
            "component_scope": components,
            "matched_apis": matched_apis,
            "missing_info": missing_info
        }

    def _resolve_api_contract(
            self,
            api_identity: ApiIdentity,
            component_version: str,
            component_source: str = "BASELINE"
    ) -> ResolvedApiContract:
        doc_resolution = self.resolve_component_doc_version(
            component_id=api_identity.component_id,
            component_version=component_version,
            segment_id=api_identity.segment_id or ""
        )
        doc_version = doc_resolution["resolved_doc_version"]
        contract = None
        lifecycle_status = "UNKNOWN"
        contract_risk = ""

        if doc_version:
            contract = self.design_repo.get_api_contract(
                api_identity_id=api_identity.id,
                doc_version=doc_version
            )
            lifecycle_status = self.design_repo.get_api_lifecycle_status(
                api_identity_id=api_identity.id,
                doc_version=doc_version
            )

        if not contract:
            contract_versions = self.design_repo.list_api_contract_versions(
                api_identity_id=api_identity.id
            )
            fallback = find_nearest_doc_version(
                component_version=doc_version or component_version,
                doc_versions=contract_versions
            )
            if fallback["doc_version"]:
                contract = self.design_repo.get_api_contract(
                    api_identity_id=api_identity.id,
                    doc_version=fallback["doc_version"]
                )
                contract_risk = (
                    f"目标文档版本 {doc_version} 没有独立契约，"
                    f"使用契约版本 {fallback['doc_version']} 推断。"
                )
                doc_version = fallback["doc_version"]

        risks = [
            item
            for item in [
                doc_resolution.get("risk", ""),
                contract_risk
            ]
            if item
        ]

        return ResolvedApiContract(
            api_identity=api_identity,
            api_contract=contract,
            requested_component_version=component_version,
            resolved_doc_version=doc_version,
            match_level=doc_resolution["match_level"],
            confidence=doc_resolution["confidence"],
            risk=" ".join(risks),
            lifecycle_status=lifecycle_status,
            component_source=component_source
        )

    def get_api_detail(
            self,
            component_id: str,
            method: str,
            api_path: str,
            component_version: str,
            segment_id: str | None = ""
    ):
        component_id = normalize_identifier(component_id)
        if segment_id is not None:
            segment_id = normalize_identifier(segment_id)
        identity = self.design_repo.find_api_identity_by_key(
            component_id=component_id,
            method=method,
            api_path=api_path,
            segment_id=segment_id
        )

        if not identity:
            return {
                "found": False,
                "message": "未找到接口身份",
                "api": None
            }

        resolved = self._resolve_api_contract(
            api_identity=identity,
            component_version=component_version
        )

        return {
            "found": True,
            "api": resolved.to_dict()
        }

    def health_check(self):
        self.design_repo.ping()

        return {
            "status": "ok",
            "message": "KnowledgeService is running",
            "model": "api_identity_contract",
            "database": "ok"
        }
