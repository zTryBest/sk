# -*- coding: utf-8 -*-

import logging
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import EMBEDDING_DIM, VECTOR_BACKEND  # noqa: E402
from repository.design_repository import DesignRepository  # noqa: E402
from service.knowledge_service import KnowledgeService  # noqa: E402
from vector.factory import create_vector_store  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _remove_if_exists(path: str):
    if os.path.exists(path):
        os.remove(path)


def _reset_store(index_file: str, mapping_file: str):
    _remove_if_exists(index_file)
    _remove_if_exists(mapping_file)
    return create_vector_store(
        backend=VECTOR_BACKEND,
        index_file=index_file,
        mapping_file=mapping_file,
        dimension=EMBEDDING_DIM
    )


def rebuild_api_identity_index():
    service = KnowledgeService()
    repo = DesignRepository()
    store = _reset_store(
        index_file="faiss_data/api_identity.index",
        mapping_file="faiss_data/api_identity_mapping.json"
    )

    for api_identity_id in repo.list_api_identity_ids():
        api_identity = repo.get_api_identity_by_id(
            api_identity_id
        )
        content = DesignRepository._api_identity_content(
            api_identity
        )
        store.add_vector(
            db_id=api_identity_id,
            embedding=service._get_embedding(content)
        )

    logger.info(
        "API身份向量索引重建完成，共 %s 条",
        store.count()
    )


if __name__ == "__main__":
    rebuild_api_identity_index()
