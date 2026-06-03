# -*- coding: utf-8 -*-

import logging
import time

from api_validation_job import run_once

from config.config import API_VALIDATION_INTERVAL_SECONDS


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception as e:
            logger.exception(
                "接口验证任务执行失败: %s",
                e
            )

        logger.info(
            "等待下一次接口验证，间隔 %s 秒",
            API_VALIDATION_INTERVAL_SECONDS
        )
        time.sleep(
            API_VALIDATION_INTERVAL_SECONDS
        )
