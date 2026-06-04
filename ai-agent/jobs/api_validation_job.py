# -*- coding: utf-8 -*-

import json
import logging
import sys
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import (  # noqa: E402
    API_VALIDATION_LIMIT,
    API_VALIDATION_TIMEOUT,
    TEST_ENV_BASE_URL,
)
from models.api_validation import ApiValidationRecord  # noqa: E402
from repository.api_validation_repository import ApiValidationRepository  # noqa: E402
from repository.design_repository import DesignRepository  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _build_url(base_url: str, api_path: str) -> str:
    return f"{base_url.rstrip('/')}/{api_path.lstrip('/')}"


def _extract_schema_snapshot(response_text: str):
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return {}

    if isinstance(payload, dict):
        return {
            key: type(value).__name__
            for key, value in payload.items()
        }

    if isinstance(payload, list):
        return {
            "type": "list",
            "item_count": len(payload)
        }

    return {
        "type": type(payload).__name__
    }


def _call_api(
        url: str,
        method: str,
        headers: dict,
        body: dict,
        timeout: int
):
    normalized_method = (method or "GET").upper()
    data = None
    request_headers = dict(headers or {})

    if body:
        data = json.dumps(
            body,
            ensure_ascii=False
        ).encode("utf-8")
        request_headers.setdefault(
            "Content-Type",
            "application/json"
        )

    req = urllib_request.Request(
        url=url,
        data=data,
        headers=request_headers,
        method=normalized_method
    )

    with urllib_request.urlopen(
            req,
            timeout=timeout
    ) as response:
        response_body = response.read().decode(
            "utf-8",
            errors="replace"
        )

        return response.status, response_body


def run_once(
        base_url: str = TEST_ENV_BASE_URL,
        limit: int = API_VALIDATION_LIMIT,
        timeout: int = API_VALIDATION_TIMEOUT
):
    if not base_url:
        raise RuntimeError(
            "请先配置 TEST_ENV_BASE_URL，再运行接口验证任务。"
        )

    design_repo = DesignRepository()
    validation_repo = ApiValidationRepository()

    targets = design_repo.list_contract_validation_targets(
        limit=limit
    )

    logger.info(
        "开始验证接口契约，共 %s 个目标",
        len(targets)
    )

    for target in targets:
        identity = target["identity"]
        contract = target["contract"]
        request_url = _build_url(
            base_url,
            identity.api_path
        )
        response_status = None
        response_body = ""
        error_message = ""

        try:
            response_status, response_body = _call_api(
                url=request_url,
                method=identity.method,
                headers=contract.request_headers,
                body=contract.request_example,
                timeout=timeout
            )
            is_success = 200 <= response_status < 300
        except urllib_error.HTTPError as e:
            response_status = e.code
            response_body = e.read().decode(
                "utf-8",
                errors="replace"
            )
            error_message = str(e)
            is_success = False
        except Exception as e:
            error_message = str(e)
            is_success = False

        validation_repo.save(
            ApiValidationRecord(
                api_id=None,
                product_id="",
                product_version="",
                component_id=identity.component_id,
                segment_id=identity.segment_id,
                component_version="",
                test_env=base_url,
                request_url=request_url,
                request_method=identity.method,
                request_headers=contract.request_headers,
                request_body=contract.request_example,
                response_status=response_status,
                response_body=response_body,
                response_schema_snapshot=_extract_schema_snapshot(
                    response_body
                ),
                is_success=is_success,
                error_message=error_message,
                api_identity_id=identity.id,
                api_contract_id=contract.id,
                resolved_doc_version=contract.doc_version
            )
        )

        logger.info(
            "接口契约验证完成 identity_id=%s contract_id=%s success=%s http=%s",
            identity.id,
            contract.id,
            is_success,
            response_status
        )


if __name__ == "__main__":
    run_once()
