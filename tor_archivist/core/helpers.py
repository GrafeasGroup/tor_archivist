import logging
import re
import signal
import sys
import time
from typing import Any, Callable
from urllib.parse import urlparse

import praw
import prawcore

from tor_archivist.core import __version__
from tor_archivist.core.config import config
from tor_archivist.core.strings import bot_footer

default_exceptions = (
    prawcore.exceptions.RequestException,
    prawcore.exceptions.ServerError,
    prawcore.exceptions.Forbidden,
)

# error message for an API timeout
_pattern = re.compile(r"again in (?P<number>[0-9]+) (?P<unit>\w+)s?\.$", re.IGNORECASE)

# CTRL+C handler variable
running = True


def get_id_from_url(url: str) -> str:
    """Extract and return the ID from the end of a Blossom URL."""
    return list(filter(None, urlparse(url).path.split("/")))[-1]


def _(message: str) -> str:
    """Return the message wrapped in the bot footer.

    :param message: The message to be displayed.
    :return: The original message plus the footer.
    """
    return bot_footer.format(message, version=__version__)


def log_header(message: str) -> None:
    """Create a pretty header for the given message."""
    logging.info("*" * 50)
    logging.info(message)
    logging.info("*" * 50)


def explode_gracefully(error: RuntimeError) -> None:
    """Shut down the bot due to an error, logging the error in the meantime.

    A last-ditch effort to try to raise a few more flags as it goes down.
    Only call in times of dire need.

    :param bot_name: string; the name of the bot calling the method.
    :param error: an exception object.
    :param tor: the r/ToR helper object
    :return: Nothing. Everything dies here.
    """
    logging.exception(error, exc_info=True)
    sys.exit(1)


def handle_rate_limit(exc: Any) -> None:
    """Handle the Reddit rate limit."""
    time_map = {
        "second": 1,
        "minute": 60,
        "hour": 60 * 60,
    }
    matches = re.search(_pattern, exc.message)

    if matches is not None:
        delay = int(matches[0]) * time_map[matches[1]]
        time.sleep(delay + 1)


def signal_handler(signal: Any, frame: Any) -> None:
    """Handle SIGINT events.

    This is the SIGINT handler that allows us to intercept CTRL+C.
    When this is triggered, it will wait until the primary loop ends
    the current iteration before ending. Press CTRL+C twice to kill
    immediately.

    :param signal: Unused.
    :param frame: Unused.
    :return: None.
    """
    global running

    if not running:
        logging.critical("User pressed CTRL+C twice!!! Killing!")
        sys.exit(1)

    logging.info("\rUser triggered command line shutdown. Will terminate after current loop.")
    running = False


def run_until_dead(func: Callable, exceptions: tuple = default_exceptions) -> None:
    """Run the function until it gets killed by the user.

    The official method that replaces all that ugly boilerplate required to
    start up a bot under the TranscribersOfReddit umbrella. This method handles
    communication issues with Reddit, timeouts, and handles CTRL+C and
    unexpected crashes.

    :param func: The function that you want to run; this will automatically be
        passed the config object. Historically, this is the only thing needed
        to start a bot.
    :param exceptions: A tuple of exception classes to guard against. These are
        a set of PRAW connection errors (timeouts and general connection
        issues) but they can be overridden with a passed-in set.
    :return: None.
    """
    # handler for CTRL+C
    signal.signal(signal.SIGINT, signal_handler)

    try:
        while running:
            try:
                func(config)
            except praw.exceptions.APIException as e:
                if e.error_type == "RATELIMIT":
                    logging.warning(
                        "Ratelimit - artificially limited by Reddit. Sleeping"
                        " for requested time!"
                    )
                    handle_rate_limit(e)
            except exceptions as e:
                logging.warning(f"{e} - Issue communicating with Reddit. Sleeping for 60s!")
                time.sleep(60)

        logging.info("User triggered shutdown. Shutting down.")
        sys.exit(0)

    except Exception as e:
        explode_gracefully(e)
