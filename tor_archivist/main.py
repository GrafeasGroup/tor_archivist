import argparse
import logging
import os
import pathlib
import sys
import time
from typing import Any, Dict

import click
from click.core import Context
import dotenv
from blossom_wrapper import BlossomStatus

from tor_archivist import (
    CLEAR_THE_QUEUE_MODE,
    NOOP_MODE,
    DEBUG_MODE,
    UPDATE_DELAY_SEC,
    ARCHIVING_RUN_STEPS,
    DISABLE_COMPLETED_ARCHIVING,
    DISABLE_EXPIRED_ARCHIVING,
    DISABLE_POST_REMOVAL_TRACKING,
    DISABLE_POST_REPORT_TRACKING,
    __version__,
)
from tor_archivist.core.config import Config
from tor_archivist.core.config import config
from tor_archivist.core.helpers import run_until_dead, get_id_from_url
from tor_archivist.core.initialize import build_bot
from tor_archivist.core.queue_sync import track_post_removal, track_post_reports

dotenv.load_dotenv()


def run_noop(*args: Any) -> None:
    time.sleep(10)
    logging.info("Loop!")


def process_expired_posts(cfg: Config) -> None:
    response = cfg.blossom.get_expired_submissions()

    if response.status != BlossomStatus.ok:
        logging.warning("Received bad response from Blossom. Cannot process.")
        return

    if hasattr(response, "data"):
        for b_submission in response.data:
            # Only archived if it hasn't been removed already
            r_submission = cfg.reddit.submission(url=b_submission["tor_url"])

            if not r_submission.removed_by_category:
                r_submission.mod.remove()
                cfg.blossom.archive_submission(submission_id=b_submission["id"])
                logging.info(
                    f"Archived expired submission {b_submission['id']}"
                    f" ({b_submission['tor_url']})"
                )


def get_human_transcription(cfg: Config, submission: Dict) -> Dict:
    response = cfg.blossom.get(
        "transcription/search/", params={"submission_id": submission["id"]}
    )
    for transcription in response.json():
        if int(get_id_from_url(transcription["author"])) == config.transcribot["id"]:
            continue
        else:
            return transcription


def archive_completed_posts(cfg: Config) -> None:
    response = cfg.blossom.get_unarchived_submissions()

    if response.status != BlossomStatus.ok:
        logging.warning("Received bad response from Blossom. Cannot process.")
        return

    if hasattr(response, "data"):
        for submission in response.data:
            reddit_post = cfg.reddit.submission(url=submission["tor_url"])
            reddit_post.mod.remove()
            cfg.blossom.archive_submission(submission_id=submission["id"])

            transcription = get_human_transcription(cfg, submission)

            if not transcription:
                logging.warning(
                    f"Received completed post ID {submission['id']} with no valid"
                    f" transcriptions."
                )
                # This means that we _should not_ make a post on r/ToR_Archive
                # because there's no transcription to link to.
                continue

            if not transcription.get("url"):
                logging.warning(
                    f"Transcription {transcription['id']} does not have a URL"
                    f" - skipping."
                )
                continue

            if "reddit.com" not in transcription["url"]:
                transcription["url"] = f"https://reddit.com{transcription['url']}"

            cfg.archive.submit(reddit_post.title, url=transcription["url"])
            logging.info(
                f"Submission {submission['id']} ({submission['tor_url']}) archived!"
            )


def run(cfg: Config) -> None:
    if not CLEAR_THE_QUEUE_MODE and cfg.sleep_until >= time.time():
        # TODO: if ctq is active, send ctq query parameter to expired endpoint
        # This is how we sleep for longer periods, but still respond to
        # CTRL+C quickly: trigger an event loop every few seconds during wait
        # time.
        time.sleep(5)
        return

    if CLEAR_THE_QUEUE_MODE:
        logging.info("Clear the Queue Mode is engaged!")
    else:
        cfg.sleep_until = time.time() + UPDATE_DELAY_SEC

    logging.info(f"Starting cycle (step {cfg.archive_run_step}/{ARCHIVING_RUN_STEPS})")

    # Skip every couple archiving runs for better performance
    # The queue sync stuff is more important to run frequently
    if cfg.archive_run_step >= ARCHIVING_RUN_STEPS:
        logging.info("Starting archiving of old posts...")
        if not DISABLE_COMPLETED_ARCHIVING:
            archive_completed_posts(cfg)
        else:
            logging.info("Archiving of completed posts is disabled!")
        if not DISABLE_EXPIRED_ARCHIVING:
            process_expired_posts(cfg)
        else:
            logging.info("Archiving of expired posts is disabled!")
        # Reset counter
        cfg.archive_run_step = 0
    else:
        # Skip archiving step
        pass
    # Queue sync stuff
    if not DISABLE_POST_REMOVAL_TRACKING:
        track_post_removal(cfg)
    else:
        logging.info("Tracking of post removals is disabled!")
    if not DISABLE_POST_REPORT_TRACKING:
        track_post_reports(cfg)
    else:
        logging.info("Tracking of post reports is disabled!")

    # Increment run step
    cfg.archive_run_step += 1


@click.group(
    context_settings=dict(help_option_names=["-h", "--help", "--halp"]),
    invoke_without_command=True,
)
@click.pass_context
@click.option(
    "-d",
    "--debug",
    "debug",
    is_flag=True,
    default=DEBUG_MODE,
    help="Puts bot in dev-mode using non-prod credentials",
)
@click.option(
    "-n",
    "--noop",
    "noop",
    is_flag=True,
    default=NOOP_MODE,
    help="Just run the daemon, but take no action (helpful for testing infrastructure changes)",
)
@click.version_option(version=__version__, prog_name="tor_archivist")
def main(ctx: Context, debug: bool, noop: bool) -> None:
    if ctx.invoked_subcommand:
        # If we asked for a specific command, don't run the bot. Instead, pass control
        # directly to the subcommand.
        return

    config.debug_mode = debug
    bot_name = "debug" if config.debug_mode else "tor_archivist"

    build_bot(bot_name, __version__)

    config.archive = config.reddit.subreddit(
        os.environ.get("ARCHIVE_SUBREDDIT", "ToR_Archive")
    )
    config.tor = config.reddit.subreddit(
        os.environ.get("TOR_SUBREDDIT", "TranscribersOfReddit")
    )

    # jumpstart the clock -- allow running immediately after starting.
    config.sleep_until = 0
    if noop:
        run_until_dead(run_noop)
    else:
        run_until_dead(run)


@main.command()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show Pytest output instead of running quietly.",
)
def selfcheck(verbose: bool) -> None:
    """
    Verify the binary passes all tests internally.

    Add any other self-check related code here.
    """
    import pytest

    import tor_archivist.test

    # -x is 'exit immediately if a test fails'
    # We need to get the path because the file is actually inside the extracted
    # environment maintained by shiv, not physically inside the archive at the
    # time of running.
    args = ["-x", str(pathlib.Path(tor_archivist.test.__file__).parent)]
    if not verbose:
        args.append("-qq")
    # pytest will return an exit code that we can check on the command line
    sys.exit(pytest.main(args))


BANNER = r"""
___________   __________        _____                .__    .__      .__          __
\__    ___/___\______   \      /  _  \_______   ____ |  |__ |__|__  _|__| _______/  |_
  |    | /  _ \|       _/     /  /_\  \_  __ \_/ ___\|  |  \|  \  \/ /  |/  ___/\   __\
  |    |(  <_> )    |   \    /    |    \  | \/\  \___|   Y  \  |\   /|  |\___ \  |  |
  |____| \____/|____|_  /____\____|__  /__|    \___  >___|  /__| \_/ |__/____  > |__|
                      \/_____/       \/            \/     \/                 \/
"""


@main.command()
def shell() -> None:
    """Create a Python REPL inside the environment."""
    import code

    code.interact(local=globals(), banner=BANNER)


if __name__ == "__main__":
    main()
