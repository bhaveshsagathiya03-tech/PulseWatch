import json
from app.core.config import settings


def get_redis():
    try:
        import redis
    except ImportError as exc:
        raise RuntimeError("Redis client is not installed. Install backend requirements.") from exc
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=3)
    client.ping()
    return client


def publish_event(project_id: str, payload: dict) -> str:
    client = get_redis()
    return client.xadd(settings.redis_stream, {"project_id": project_id, "payload": json.dumps(payload, default=str)}, maxlen=100000, approximate=True)
