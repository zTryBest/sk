# -*- coding: utf-8 -*-

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from service.knowledge_service import KnowledgeService  # noqa: E402


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _identity_summary(identity, score_map, terms, service):
    contracts = service.design_repo.list_api_contracts(
        identity.id
    )
    content = service.design_repo.build_api_search_content(
        identity,
        contracts
    )
    keyword_score = service._term_overlap_score(
        terms,
        content
    )
    return {
        "id": identity.id,
        "component_id": identity.component_id,
        "segment_id": identity.segment_id,
        "method": identity.method,
        "api_path": identity.api_path,
        "api_name": identity.api_name,
        "vector_score": score_map.get(identity.id),
        "keyword_score": keyword_score,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Debug design-phase API retrieval for one requirement."
    )
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--product-version", required=True)
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--vector-top-k", type=int, default=30)
    parser.add_argument(
        "--component-overrides",
        default="{}",
        help='JSON object, for example {"AAA":"v1.2"}',
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    service = KnowledgeService()
    component_overrides = json.loads(args.component_overrides)
    components = service._resolve_product_components(
        product_id=args.product_id,
        product_version=args.product_version,
        component_overrides=component_overrides,
    )
    component_ids = [
        item["component_id"]
        for item in components
    ]
    terms = service._extract_search_terms(args.requirement)

    query_embedding = service._get_embedding(args.requirement)
    vector_candidates = service.api_identity_vector_store.search(
        query_embedding,
        top_k=args.vector_top_k,
    )
    candidate_ids = [
        item["db_id"]
        for item in vector_candidates
    ]
    score_map = {
        item["db_id"]: item["score"]
        for item in vector_candidates
    }
    filtered_identities = service.design_repo.find_api_identities_by_ids(
        ids=candidate_ids,
        component_ids=component_ids,
        limit=args.vector_top_k,
    )
    result = service.find_apis_for_requirement(
        product_id=args.product_id,
        product_version=args.product_version,
        requirement_item=args.requirement,
        component_overrides=component_overrides,
        limit=args.limit,
    )

    payload = {
        "requirement": args.requirement,
        "terms": terms,
        "component_scope": components,
        "raw_vector_top": vector_candidates,
        "filtered_vector_top": [
            _identity_summary(
                identity,
                score_map,
                terms,
                service,
            )
            for identity in filtered_identities
        ],
        "final_matches": [
            {
                "id": item["api_identity"]["id"],
                "component_id": item["api_identity"]["component_id"],
                "segment_id": item["api_identity"].get("segment_id", ""),
                "method": item["api_identity"]["method"],
                "api_path": item["api_identity"]["api_path"],
                "api_name": item["api_identity"]["api_name"],
                "score": item.get("score"),
                "vector_score": item.get("vector_score"),
                "keyword_score": item.get("keyword_score"),
                "match_source": item.get("match_source"),
                "resolved_doc_version": item.get("resolved_doc_version"),
                "risk": item.get("risk"),
            }
            for item in result["matched_apis"]
        ],
        "missing_info": result["missing_info"],
    }

    if args.json:
        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=_json_default,
            )
        )
        return

    print("Requirement:", payload["requirement"])
    print("Terms:", ", ".join(payload["terms"]))
    print("Components:", ", ".join(component_ids))
    print("\nRaw vector top:")
    for item in payload["raw_vector_top"]:
        print(f"  id={item['db_id']} score={item['score']}")
    print("\nFiltered vector top:")
    for item in payload["filtered_vector_top"]:
        print(
            f"  id={item['id']} score={item['vector_score']} "
            f"keyword={item['keyword_score']} "
            f"{item['component_id']}/{item['segment_id']} "
            f"{item['method']} {item['api_path']} {item['api_name']}"
        )
    print("\nFinal matches:")
    for item in payload["final_matches"]:
        print(
            f"  id={item['id']} score={item['score']} "
            f"vector={item['vector_score']} keyword={item['keyword_score']} "
            f"{item['component_id']}/{item['segment_id']} "
            f"{item['method']} {item['api_path']} {item['api_name']}"
        )


if __name__ == "__main__":
    main()
