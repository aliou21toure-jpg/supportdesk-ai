from functools import lru_cache

from redis import Redis
from rq import Queue, Retry

from app.config import get_settings


@lru_cache
def get_queue() -> Queue:
    settings = get_settings()
    return Queue(settings.queue_name, connection=Redis.from_url(settings.redis_url))


def enqueue_triage(ticket_id: str) -> None:
    # Retry transient failures (rate limits, timeouts) with increasing delays.
    get_queue().enqueue(
        "app.jobs.triage_ticket",
        ticket_id,
        retry=Retry(max=3, interval=[10, 30, 90]),
        job_timeout=120,
    )
