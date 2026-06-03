# -*- coding: utf-8 -*-

import json
import logging
import os

import faiss
import numpy as np

from vector.base import BaseVectorStore, VectorSearchResult


logger = logging.getLogger(__name__)


class FaissVectorStore(BaseVectorStore):

    def __init__(
            self,
            index_file: str,
            mapping_file: str,
            dimension: int = 1024
    ):

        self.index_file = index_file
        self.mapping_file = mapping_file
        self.dimension = dimension

        os.makedirs(
            os.path.dirname(index_file),
            exist_ok=True
        )

        self.index = self._load_index()

        self.id_mapping = self._load_mapping()

        logger.info(
            f"FaissVectorStore初始化完成，当前向量数={self.index.ntotal}"
        )

    # =====================================
    # 加载索引
    # =====================================

    def _load_index(self):

        if not os.path.exists(
                self.index_file
        ):

            logger.info(
                "索引文件不存在，创建新索引"
            )

            return faiss.IndexHNSWFlat(
                self.dimension,
                32
            )

        try:

            logger.info(
                f"加载索引: {self.index_file}"
            )

            return faiss.read_index(
                self.index_file
            )

        except Exception as e:

            logger.error(
                f"索引加载失败: {e}"
            )

            logger.warning(
                "重新创建新索引"
            )

            return faiss.IndexHNSWFlat(
                self.dimension,
                32
            )

    # =====================================
    # 加载映射
    # =====================================

    def _load_mapping(self):

        if not os.path.exists(
                self.mapping_file
        ):
            return {}

        try:

            with open(
                    self.mapping_file,
                    "r",
                    encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception as e:

            logger.error(
                f"映射文件加载失败: {e}"
            )

            return {}

    # =====================================
    # 保存
    # =====================================

    def save(self):

        logger.info(
            "保存Faiss索引"
        )

        faiss.write_index(
            self.index,
            self.index_file
        )

        with open(
                self.mapping_file,
                "w",
                encoding="utf-8"
        ) as f:

            json.dump(
                self.id_mapping,
                f,
                ensure_ascii=False,
                indent=2
            )

    # =====================================
    # 新增向量
    # =====================================

    def add_vector(
            self,
            db_id: int,
            embedding: list
    ):

        try:

            vector = np.array(
                [embedding],
                dtype=np.float32
            )

            faiss.normalize_L2(
                vector
            )

            current_id = self.index.ntotal

            self.index.add(
                vector
            )

            self.id_mapping[
                str(current_id)
            ] = db_id

            self.save()

            logger.info(
                f"新增向量成功 db_id={db_id}"
            )

        except Exception as e:

            logger.exception(
                f"新增向量失败: {e}"
            )

            raise

    # =====================================
    # 查询
    # =====================================

    def search(
            self,
            embedding: list,
            top_k: int = 10
    ) -> list[dict]:

        if self.index.ntotal == 0:

            logger.info(
                "索引为空"
            )

            return []

        try:

            vector = np.array(
                [embedding],
                dtype=np.float32
            )

            faiss.normalize_L2(
                vector
            )

            scores, ids = self.index.search(
                vector,
                top_k
            )

            result = []

            for distance, idx in zip(
                    scores[0],
                    ids[0]
            ):

                if idx < 0:
                    continue

                db_id = self.id_mapping.get(
                    str(idx)
                )

                if db_id is None:
                    continue

                result.append(
                    VectorSearchResult(
                        db_id=int(db_id),
                        score=1.0 - (float(distance) / 2.0)
                    ).to_dict()
                )

            return result

        except Exception as e:

            logger.exception(
                f"查询失败: {e}"
            )

            raise

    # =====================================
    # 当前向量数
    # =====================================

    def count(self):

        return self.index.ntotal
