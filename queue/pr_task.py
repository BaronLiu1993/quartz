from .config import app
from service.pr_service import route_event

@app.task(name="pr.process_event")
def process_pr_event(event: str, payload: dict):
    return route_event(event, payload)