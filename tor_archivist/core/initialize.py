import logging
import os

from blossom_wrapper import BlossomAPI
from bugsnag.handlers import BugsnagHandler
from praw import Reddit

from tor_archivist.core.config import config
from tor_archivist.core.helpers import log_header


def has_tor_environment_vars():
    for var in ("username", "password", "client_id", "client_secret", "user_agent"):
        if f"praw_{var}" not in os.environ:
            return False

    return True


def configure_tor(config):
    """
    Assembles the tor object based on whether or not we've enabled debug mode
    and returns it. There's really no reason to put together a Subreddit
    object dedicated to our subreddit -- it just makes some future lines
    a little easier to type.

    :param r: the active Reddit object.
    :param config: the global config object.
    :return: the Subreddit object for the chosen subreddit.
    """
    if config.debug_mode:
        tor = config.reddit.subreddit("ModsOfToR")
    else:
        # normal operation, our primary subreddit
        tor = config.reddit.subreddit("transcribersofreddit")

    return tor


def configure_logging(config):
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # will intercept anything error level or above
    if config.bugsnag_api_key:
        bs_handler = BugsnagHandler()
        bs_handler.setLevel(logging.ERROR)
        logging.getLogger("").addHandler(bs_handler)
        logging.info("Bugsnag enabled!")
    else:
        logging.info("Not running with Bugsnag!")

    log_header("Starting!")


def get_blossom_connection():
    return BlossomAPI(
        email=os.getenv("BLOSSOM_EMAIL"),
        password=os.getenv("BLOSSOM_PASSWORD"),
        api_key=os.getenv("BLOSSOM_API_KEY"),
    )


def get_user_info(config, username: str = None) -> None:
    if not username:
        username = "tor_archivist"
    return config.blossom.get("volunteer/", params={"username": username}).json()[
        "results"
    ][0]


def build_bot(
    name,
    version,
):
    """
    Shortcut for setting up a bot instance. Runs all configuration and returns
    a valid config object.

    :param name: string; The name of the bot to be started; this name must
        match the settings in praw.ini
    :param version: string; the version number for the current bot being run
    :param full_name: string; the descriptive name of the current bot being
        run; this is used for the heartbeat and status
    :param log_name: string; the name to be used for the log file on disk. No
        spaces.
    :param require_redis: bool; triggers the creation of the Redis instance.
        Any bot that does not require use of Redis can set this to False and
        not have it crash on start because Redis isn't running.
    :return: None
    """

    if has_tor_environment_vars():
        config.reddit = Reddit()
    else:
        config.reddit = Reddit(name)

    # PRAW 7 has a weird behavior with the flag `validate_on_submit`. If we
    # submit something without touching this flag at all (e.g. the old way)
    # then it yells at us for having it set to false.
    #
    # The documentation says that it's deprecated since version 7.0.
    # The changelog says that it's going away.
    # But it still yells at us for not setting it.
    #
    # We can't check to see if it exists with hasattr, because somehow that
    # triggers the yelling. So for now, we'll just set the variable to True
    # and when PRAW finally does remove this attribute, we'll just be setting
    # a useless attribute and it shouldn't hurt anything. Should definitely
    # check on this again around PRAW 8, though.
    config.reddit.validate_on_submit = True

    config.name = name
    config.bot_version = version
    configure_logging(config)

    config.blossom = get_blossom_connection()
    config.me = get_user_info(config)
    config.transcribot = get_user_info(config, "transcribot")

    logging.info("Bot built and initialized!")
