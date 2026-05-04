from celery import Celery
from kombu import Queue

app = Celery(
    "quartz",
    broker="amqp://guest:guest@localhost:5672//",
    include=["async_queue.pr_task"],
)

app.conf.task_queues = (
    Queue("ingestion"),
    Queue("pr"),
)

app.conf.task_routes = {
    "ingestion.*": {"queue": "ingestion"},
    "pr.*": {"queue": "pr"},
}