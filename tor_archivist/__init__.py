__version__ = "0.7.3"

import os

CLEAR_THE_QUEUE_MODE = bool(os.getenv("CLEAR_THE_QUEUE", ""))
NOOP_MODE = bool(os.getenv("NOOP_MODE", ""))
DEBUG_MODE = bool(os.getenv("DEBUG_MODE", ""))

UPDATE_DELAY_SEC = int(os.getenv("UPDATE_DELAY_SEC", 60))
ARCHIVING_RUN_STEPS = int(os.getenv("ARCHIVING_RUN_STEPS", 10))

DISABLE_COMPLETED_ARCHIVING = bool(os.getenv("DISABLE_COMPLETED_ARCHIVING", False))
DISABLE_EXPIRED_ARCHIVING = bool(os.getenv("DISABLE_EXPIRED_ARCHIVING", False))
DISABLE_POST_REMOVAL_TRACKING = bool(os.getenv("DISABLE_POST_REMOVAL_TRACKING", False))
DISABLE_POST_REPORT_TRACKING = bool(os.getenv("DISABLE_POST_REPORT_TRACKING", False))

# TODO: Remove the lines below with hardcoded versions.
__VERSION__ = "1.0.0"
