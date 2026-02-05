"""Application settings using Pydantic."""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # GCP Settings
    gcp_project_id: str = Field(..., env="GCP_PROJECT_ID")
    gcp_region: str = Field(default="us-central1", env="GCP_REGION")
    gcp_storage_bucket: str = Field(..., env="GCP_STORAGE_BUCKET")

    # Firestore
    firestore_collection_docs: str = Field(default="documents", env="FIRESTORE_COLLECTION_DOCS")

    # Pub/Sub Topics
    pubsub_topic_ocr: str = Field(default="ocr-process", env="PUBSUB_TOPIC_OCR")
    pubsub_topic_index: str = Field(default="index-doc", env="PUBSUB_TOPIC_INDEX")

    # Vector DB
    vector_db_type: str = Field(default="qdrant", env="VECTOR_DB_TYPE")  # qdrant | vertex
    qdrant_url: Optional[str] = Field(default=None, env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="mamimind_docs", env="QDRANT_COLLECTION")

    # LLM Settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    default_llm: str = Field(default="gpt-4-turbo-preview", env="DEFAULT_LLM")
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")

    # OCR Settings
    ocr_engine: str = Field(default="google", env="OCR_ENGINE")  # google | tesseract

    # RAG Settings
    rag_top_k: int = Field(default=5, env="RAG_TOP_K")
    rag_similarity_threshold: float = Field(default=0.7, env="RAG_SIMILARITY_THRESHOLD")

    # Agent Settings
    agent_max_retries: int = Field(default=3, env="AGENT_MAX_RETRIES")
    agent_timeout: int = Field(default=300, env="AGENT_TIMEOUT")

    # Observability
    enable_tracing: bool = Field(default=True, env="ENABLE_TRACING")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
