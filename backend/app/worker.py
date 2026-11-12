"""Redis Streams worker with retry, pending-message recovery and dead-letter handling."""
import json
import logging
import os
import socket
import time
from app.core.config import settings
from app.db.session import SessionLocal
from app import models  # noqa: F401 - register model metadata
from app.queue import get_redis
from app.services.processing import process_event

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pulsewatch.worker")
CLAIM_IDLE_MS = int(os.getenv("REDIS_CLAIM_IDLE_MS", "60000"))


def ensure_group(client):
    try:
        client.xgroup_create(settings.redis_stream, settings.redis_group, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def process_message(client, stream_id: str, values: dict):
    try:
        project_id = values["project_id"]
        payload = json.loads(values["payload"])
        with SessionLocal() as db:
            result = process_event(db, project_id, payload)
        client.xack(settings.redis_stream, settings.redis_group, stream_id)
        client.delete(f"pulsewatch:attempts:{stream_id}")
        log.info("Processed event %s into issue %s", payload.get("event_id"), result.get("issue_id"))
    except Exception:
        log.exception("Failed event %s", stream_id)
        attempts_key = f"pulsewatch:attempts:{stream_id}"
        attempts = client.incr(attempts_key)
        client.expire(attempts_key, 86400)
        if attempts >= 5:
            client.xadd(settings.redis_dead_letter_stream, {"original_id": stream_id, **values})
            client.xack(settings.redis_stream, settings.redis_group, stream_id)
            log.error("Moved stream event %s to dead-letter stream", stream_id)
        else:
            time.sleep(min(attempts * 2, 10))


def recover_pending(client, consumer: str):
    """Claim entries abandoned by crashed consumers (Redis 6.2+)."""
    try:
        result = client.xautoclaim(
            settings.redis_stream, settings.redis_group, consumer,
            min_idle_time=CLAIM_IDLE_MS, start_id="0-0", count=20,
        )
        if result and len(result) >= 2:
            messages = result[1]
            for stream_id, values in messages:
                process_message(client, stream_id, values)
    except AttributeError:
        log.warning("Redis client does not expose XAUTOCLAIM; pending recovery is unavailable")
    except Exception:
        log.exception("Pending-message recovery failed")


def main():
    client = get_redis()
    ensure_group(client)
    consumer = f"{socket.gethostname()}-{os.getpid()}"
    log.info("Worker started as %s", consumer)
    last_recovery = 0.0
    while True:
        try:
            now = time.monotonic()
            if now - last_recovery >= 15:
                recover_pending(client, consumer)
                last_recovery = now
            batches = client.xreadgroup(settings.redis_group, consumer, {settings.redis_stream: ">"}, count=20, block=5000)
            for _, messages in batches:
                for stream_id, values in messages:
                    process_message(client, stream_id, values)
        except Exception:
            log.exception("Worker loop error; reconnecting")
            time.sleep(3)
            client = get_redis()
            ensure_group(client)


if __name__ == "__main__":
    main()
