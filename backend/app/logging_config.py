import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "task_id"):
            log["task_id"] = record.task_id
        return json.dumps(log)


def setup_logging():
    """Configure structured JSON logging for production, plain text for dev."""
    use_json = os.environ.get("LOG_FORMAT", "json") == "json"
    level = os.environ.get("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if use_json:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
