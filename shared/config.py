from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    elasticsearch_url: str = "http://localhost:9200"

    postgres_user: str = "finagent"
    postgres_password: str = "finagent_dev_password"
    postgres_db: str = "financial_gold"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "faq_policies"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_responses: str = "agent.responses"
    kafka_topic_dlq: str = "agent.requests.dlq"
    kafka_topic_requests: str = "agent.requests"  # legacy — use intent topics instead
    kafka_max_retries: int = 3
    kafka_disabled: bool = False

    # Set via WORKER_INTENT on intent worker containers
    worker_intent: str = ""
    worker_port: int = 8011

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_enabled: bool = True
    redis_cache_ttl_seconds: int = 300
    redis_rate_limit_per_minute: int = 30
    redis_request_state_ttl_seconds: int = 120

    dlp_agent_url: str = "http://localhost:8001"
    text_to_sql_agent_url: str = "http://localhost:8002"
    rag_agent_url: str = "http://localhost:8003"
    orchestrator_url: str = "http://localhost:8000"
    mcp_server_port: int = 8020

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
