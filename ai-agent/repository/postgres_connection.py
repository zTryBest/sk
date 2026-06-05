# -*- coding: utf-8 -*-

import logging
import threading

import psycopg2
from psycopg2 import InterfaceError, OperationalError

from config.config import POSTGRES_CONFIG


logger = logging.getLogger(__name__)


class ResilientPostgresConnection:
    """Small psycopg2 connection wrapper that reconnects after idle disconnects."""

    def __init__(self, name: str = "postgres"):
        self.name = name
        self._conn = None
        self._lock = threading.RLock()
        self._connect()

    def _connect(self):
        with self._lock:
            self._close_quietly()
            logger.info("Opening PostgreSQL connection for %s", self.name)
            self._conn = psycopg2.connect(
                **POSTGRES_CONFIG
            )
            self._conn.autocommit = True

    def _close_quietly(self):
        if self._conn is None:
            return

        try:
            if not self._conn.closed:
                self._conn.close()
        except Exception:
            logger.debug(
                "Ignoring error while closing PostgreSQL connection for %s",
                self.name,
                exc_info=True
            )

    def _ensure_connection(self):
        with self._lock:
            if self._conn is None or self._conn.closed:
                self._connect()
                return

            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            except (InterfaceError, OperationalError):
                logger.warning(
                    "PostgreSQL connection for %s is stale; reconnecting",
                    self.name,
                    exc_info=True
                )
                self._connect()

    def cursor(self, *args, **kwargs):
        self._ensure_connection()
        return self._conn.cursor(*args, **kwargs)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        with self._lock:
            self._close_quietly()
            self._conn = None

    @property
    def closed(self):
        return True if self._conn is None else self._conn.closed

    def ping(self):
        self._ensure_connection()
        return True
