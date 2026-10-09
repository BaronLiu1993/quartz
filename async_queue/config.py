from celery import Celery
from kombu import Queue
import os

app = Celery(
    "quartz",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    include=["async_queue.pr_task", "async_queue.ingest_codebase"],
)

app.conf.task_queues = (
    Queue("ingestion"),
    Queue("pr"),
)

app.conf.task_routes = {
    "ingestion.*": {"queue": "ingestion"},
    "pr.*": {"queue": "pr"},
}
