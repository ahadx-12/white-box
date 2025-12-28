from __future__ import annotations

from typing import Any

from redis import Redis
from rq import Queue


def create_queue(redis_url: str) -> Queue:
    connection = Redis.from_url(redis_url)
    return Queue("trustai", connection=connection)


def enqueue_verify(queue: Queue, job_id: str, payload: dict[str, Any]) -> str:
    queue.enqueue(
        "trustai_worker.tasks.run_deep_verify",
        job_id,
        payload,
    )
    return job_id
