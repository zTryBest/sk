# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VectorSearchResult:
    db_id: int
    score: float

    def to_dict(self):
        return {
            "db_id": self.db_id,
            "score": self.score
        }


class BaseVectorStore(ABC):
    """向量存储抽象，后续迁移 pgvector 时只替换实现层。"""

    @abstractmethod
    def add_vector(
            self,
            db_id: int,
            embedding: list
    ):
        raise NotImplementedError

    @abstractmethod
    def search(
            self,
            embedding: list,
            top_k: int = 10
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError
