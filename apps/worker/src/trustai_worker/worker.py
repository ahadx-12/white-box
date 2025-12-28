from __future__ import annotations

from redis import Redis
from rq import Connection, Queue, Worker
from trustai_api.settings import get_settings


def run_worker() -> None:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    with Connection(connection):
        worker = Worker([Queue("trustai")])
        worker.work()


if __name__ == "__main__":
    run_worker()
