"""Logging configuration utilities."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_logging(level: str, output_dir: Path) -> None:
    """Configure console and file logging."""

    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "cloud_diet.log"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )

