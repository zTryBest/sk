# -*- coding: utf-8 -*-

from vector.faiss_vector_store import FaissVectorStore


# 保留旧名称，避免现有调用方立即改动。
VectorStore = FaissVectorStore
