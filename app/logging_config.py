"""Central logging setup, called once at app startup (see app/main.py).

Level is configurable via the LOG_LEVEL env var (defaults to INFO) so a
deployed instance can turn up verbosity without a code change.
"""

import logging
import os


def setup_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
