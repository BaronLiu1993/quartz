import logging

from .config import app
from service.pr_service import route_event

logger = logging.getLogger(__name__)

@app.task(name="pr.process_event", bind=True)
def process_pr_event(self, event: str, payload: dict):
    try:
        logger.info(f"Task started: pr.process_event | event={event} | task_id={self.request.id}")
        result = route_event(event, payload)
        logger.info(f"Task completed: pr.process_event | task_id={self.request.id} | result={result}")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Task failed: pr.process_event | task_id={self.request.id} | error={str(e)}", exc_info=True)
        return {"status": "failed", "error": str(e)}