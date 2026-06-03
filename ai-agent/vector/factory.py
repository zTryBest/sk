# -*- coding: utf-8 -*-

from vector.faiss_vector_store import FaissVectorStore


def create_vector_store(
        backend: str,
        index_file: str,
        mapping_file: str,
        dimension: int
):
    normalized_backend = (backend or "faiss").lower()

    if normalized_backend == "faiss":
        return FaissVectorStore(
            index_file=index_file,
            mapping_file=mapping_file,
            dimension=dimension
        )

    raise ValueError(
        f"不支持的向量存储类型: {backend}"
    )
