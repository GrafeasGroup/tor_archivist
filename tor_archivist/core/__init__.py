"""The core functionality for the archivist bot."""
import os

__version__ = "0.6.0"

__HEARTBEAT_FILE__ = os.getenv("HEARTBEAT_FILE", "heartbeat.port")
