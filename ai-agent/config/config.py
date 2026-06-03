# -*- coding: utf-8 -*-

import os
from pathlib import Path
from dotenv import load_dotenv

# 从项目根目录加载 .env 文件
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ========================
# 数据库配置（从 .env 读取，带默认值兜底）
# ========================
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.getenv("POSTGRES_PORT", 7092)),
    "database": os.getenv("POSTGRES_DATABASE", "enterprise_knowledge_base"),
    "user": os.getenv("POSTGRES_USER", "knowledge_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "knowledge_password"),
    "connect_timeout": int(os.getenv("POSTGRES_CONNECT_TIMEOUT", 5)),
}

# ========================
# Ollama Embedding 模型配置（OpenAI-compatible API）
# ========================
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "ollama")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", 1024))
EMBEDDING_TIMEOUT = int(os.getenv("EMBEDDING_TIMEOUT", 15))
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "faiss")

# ========================
# 接口真实环境验证配置
# ========================
TEST_ENV_BASE_URL = os.getenv("TEST_ENV_BASE_URL", "")
API_VALIDATION_LIMIT = int(os.getenv("API_VALIDATION_LIMIT", 50))
API_VALIDATION_TIMEOUT = int(os.getenv("API_VALIDATION_TIMEOUT", 10))
API_VALIDATION_INTERVAL_SECONDS = int(
    os.getenv("API_VALIDATION_INTERVAL_SECONDS", 3600)
)

# ========================
# Chat 模型配置（从 .env 读取）
# ========================
CHAT_API_KEY = os.getenv("CHAT_API_KEY", "")
CHAT_BASE_URL = os.getenv("CHAT_BASE_URL", "")
CHAT_MODEL = os.getenv("CHAT_MODEL", "")

# ========================
# Chroma 配置
# ========================
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db_data")
