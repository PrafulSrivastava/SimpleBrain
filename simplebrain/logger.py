"""
simplebrain/logger.py
---------------------
Centralised logging setup for SimpleBrain.

Call setup_logging(brain_root) once at startup.  Every other module should do:

    from simplebrain.logger import get_logger
    log = get_logger(__name__)

Log file:  <brain_root>/_meta/brain.log   (always appended, rotated at 5 MB)
Stderr:    WARNING+ unless BRAIN_LOG_LEVEL=DEBUG

Environment variables:
    BRAIN_LOG_LEVEL   DEBUG | INFO | WARNING | ERROR   (default INFO)
    BRAIN_LOG_LLM     1 | 0  — whether to log full LLM prompts/responses (default 1)
"""
from __future__ import annotations
import logging
import logging.handlers
import os
import sys
from pathlib import Path

_CONFIGURED = False
_LLM_LOG_ENABLED: bool = True

# Module-level sentinel so callers can always call get_logger() safely
# before setup_logging() runs (e.g. during import)
_root_logger = logging.getLogger("simplebrain")


def setup_logging(brain_root: Path) -> None:
    global _CONFIGURED, _LLM_LOG_ENABLED

    level_name = os.getenv("BRAIN_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    _LLM_LOG_ENABLED = os.getenv("BRAIN_LOG_LLM", "1") != "0"

    # File handler — rotating, DEBUG level, full detail
    log_path = brain_root / "_meta" / "brain.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))

    # Stderr handler — INFO+ (or whatever BRAIN_LOG_LEVEL says)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(level)
    stderr_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%H:%M:%S",
    ))

    root = logging.getLogger("simplebrain")
    root.setLevel(logging.DEBUG)  # let handlers decide what to show
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(stderr_handler)
    root.propagate = False

    _CONFIGURED = True
    root.info("Logging initialised — file: %s  level: %s  llm_log: %s",
              log_path, level_name, _LLM_LOG_ENABLED)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def llm_log_enabled() -> bool:
    return _LLM_LOG_ENABLED
