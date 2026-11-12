from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "PulseWatch")
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./pulsewatch.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    public_api_base_url: str = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:8000").rstrip("/")
    event_queue_driver: str = os.getenv("EVENT_QUEUE_DRIVER", "redis")
    session_secret: str = os.getenv("SESSION_SECRET", "development-only-change-this-secret")
    session_cookie: str = os.getenv("SESSION_COOKIE", "pulsewatch_session")
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    session_ttl_hours: int = int(os.getenv("SESSION_TTL_HOURS", "168"))
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip() for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",") if origin.strip()
    )
    max_event_bytes: int = int(os.getenv("MAX_EVENT_BYTES", "262144"))
    ingest_rate_per_minute: int = int(os.getenv("INGEST_RATE_PER_MINUTE", "120"))
    redis_stream: str = os.getenv("REDIS_STREAM", "pulsewatch:events")
    redis_group: str = os.getenv("REDIS_CONSUMER_GROUP", "pulsewatch-workers")
    redis_dead_letter_stream: str = os.getenv("REDIS_DEAD_LETTER_STREAM", "pulsewatch:events:dead")


settings = Settings()
