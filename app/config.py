"""UniAssist application configuration via pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # xAI / Grok API
    xai_api_key: str = ""
    xai_model: str = "grok-4"
    xai_base_url: str = "https://api.x.ai/v1"

    # Admin
    admin_password: str = "admin123"

    # RAG (cosine distance: lower = more similar, <= 0.75 is relevant)
    similarity_threshold: float = 0.75
    top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 80

    # Rate limiting
    rate_limit_per_min: int = 30

    # Demo mode
    demo_mode: bool = False

    # Paths (relative to project root)
    chroma_persist_dir: str = "./chroma_db"
    sqlite_db_path: str = "./uniassist.db"
    knowledge_base_dir: str = "./data/knowledge_base"

    @property
    def is_llm_available(self) -> bool:
        """Check if an LLM API key is configured."""
        return bool(self.xai_api_key) and self.xai_api_key != "your_xai_api_key_here"

    @property
    def effective_demo_mode(self) -> bool:
        """Demo mode is forced if no API key is available."""
        return self.demo_mode or not self.is_llm_available


settings = Settings()
