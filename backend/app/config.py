import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Knowledge Detective API"
    DEBUG: bool = True

    # Fireworks AI
    FIREWORKS_API_KEY: str = ""
    FIREWORKS_BASE_URL: str = "https://api.fireworks.ai/inference/v1"
    FIREWORKS_MODEL: str = "accounts/fireworks/models/deepseek-v4-pro"

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password123"

    # Github
    GITHUB_TOKEN: str = ""

    # Embeddings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # Paths
    # Define directories relative to backend root
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TEST_DATA_DIR: str = os.path.abspath(os.path.join(BASE_DIR, "..", "test-data"))

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
