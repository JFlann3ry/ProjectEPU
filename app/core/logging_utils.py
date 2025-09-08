import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extra fields (attributes set via `extra=`)
        for k, v in record.__dict__.items():
            if k in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            ):
                continue
            # Avoid non-serializable objects
            try:
                json.dumps(v)
                base[k] = v
            except Exception:
                base[k] = str(v)
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


def configure_logging(settings) -> None:
    level = getattr(
        logging, (getattr(settings, "LOG_LEVEL", "INFO") or "INFO").upper(), logging.INFO
    )
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to avoid duplicates on reload
    for h in list(root.handlers):
        root.removeHandler(h)

    # Console handler
    console = logging.StreamHandler()
    if getattr(settings, "LOG_JSON", True):
        console.setFormatter(JsonFormatter())
    else:
        console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(console)

    # File handler with rotation
    log_file = getattr(settings, "LOG_FILE", "logs/app.log")
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    except Exception:
        pass
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=int(getattr(settings, "LOG_MAX_BYTES", 5_000_000)),
        backupCount=int(getattr(settings, "LOG_BACKUP_COUNT", 5)),
        encoding="utf-8",
    )
    if getattr(settings, "LOG_JSON", True):
        file_handler.setFormatter(JsonFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root.addHandler(file_handler)

    # Quiet noisy loggers if desired (optional tuning)
    for noisy in ("uvicorn", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(level)
