import argparse
import datetime
import logging
import os
import time
from typing import Any, Dict

import dotenv
from blossom_wrapper import BlossomStatus

from tor_archivist.core.config import Config
from tor_archivist.core.config import config
from tor_archivist.core.helpers import run_until_dead, get_id_from_url
from tor_archivist.core.initialize import build_bot
from tor_archivist.core.strings import reddit_url

dotenv.load_dotenv()

##############################
CLEAR_THE_QUEUE_MODE = bool(os.getenv("CLEAR_THE_QUEUE", ""))
NOOP_MODE = bool(os.getenv("NOOP_MODE", ""))
DEBUG_MODE = bool(os.getenv("DEBUG_MODE", ""))

DISABLE_COMPLETED_ARCHIVING = bool(os.getenv("DISABLE_COMPLETED_ARCHIVING", False))
DISABLE_EXPIRED_ARCHIVING = bool(os.getenv("DISABLE_EXPIRED_ARCHIVING", False))
DISABLE_POST_REMOVAL_TRACKING = bool(os.getenv("DISABLE_POST_REMOVAL_TRACKING", False))

# TODO: Remove the lines below with hardcoded versions.
__VERSION__ = "1.0.0"

##############################

thirty_minutes = 1800  # seconds


def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--version", action="version", version=__VERSION__)
    parser.add_argument(
        "--debug",
        action="store_true",
        default=DEBUG_MODE,
        help="Puts bot in dev-mode using non-prod credentials",
    )
    parser.add_argument(
        "--noop",
        action="store_true",
        default=NOOP_MODE,
        help="Just run the daemon, but take no action (helpful for testing infrastructure changes)",
    )

    return parser.parse_args()


def noop(*args: Any) -> None:
    time.sleep(10)
    logging.info("Loop!")


def process_expired_posts(cfg: Config) -> None:
    response = cfg.blossom.get_expired_submissions()

    if response.status != BlossomStatus.ok:
        logging.warning("Received bad response from Blossom. Cannot process.")
        return

    if hasattr(response, "data"):
        for submission in response.data:
            cfg.r.submission(url=submission["tor_url"]).mod.remove()
            cfg.blossom.archive_submission(submission_id=submission["id"])
            logging.info(
                f"Archived expired submission {submission['id']} - original_id"
                f" {submission['original_id']}"
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
            reddit_post = cfg.r.submission(url=submission["tor_url"])
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
                f"Submission {submission['id']} - original_id"
                f" {submission['original_id']} - archived!"
            )


def track_post_removal(cfg: Config) -> None:
    """Process the mod log and sync post removals to Blossom."""
    tor = cfg.r.subreddit("TranscribersOfReddit")
    for log in tor.mod.log(action="removelink", limit=20):
        mod = log.mod
        tor_url = "https://reddit.com" + log.target_permalink
        create_time = datetime.datetime.fromtimestamp(log.created_utc)

        if mod.name.casefold() in ["tor_archivist", "blossom"]:
            # Ignore our bots to avoid doing the same thing twice
            continue

        # Fetch the corresponding submission from Blossom
        removal_response = cfg.blossom.get("submission", params={"tor_url": tor_url})
        if not removal_response.ok:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        submissions = removal_response.json()["results"]
        if len(submissions) == 0:
            logging.warning(f"Can't find submission {tor_url} in Blossom!")
            continue
        submission = submissions[0]
        submission_id = submission["id"]

        if submission["removed_from_queue"]:
            logging.debug(f"Submission {submission_id} has already been removed.")
            continue

        removal_response = cfg.blossom.patch(f"submission/{submission_id}/remove")
        if not removal_response.ok:
            logging.warning(
                f"Failed to remove submission {submission_id} ({tor_url}) from Blossom! "
                f"({removal_response.status_code})"
            )
            continue

        logging.info(f"Removed submission {submission_id} ({tor_url}) from Blossom.")


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
        cfg.sleep_until = time.time() + thirty_minutes

    logging.info("Starting archiving of old posts...")

    if not DISABLE_COMPLETED_ARCHIVING:
        archive_completed_posts(cfg)
    else:
        logging.info("Archiving of completed posts is disabled!")
    if not DISABLE_EXPIRED_ARCHIVING:
        process_expired_posts(cfg)
    else:
        logging.info("Archiving of expired posts is disabled!")
    if not DISABLE_POST_REMOVAL_TRACKING:
        track_post_removal(cfg)
    else:
        logging.info("Tracking of post removals is disabled!")

    if not CLEAR_THE_QUEUE_MODE:
        logging.info("Finished archiving - sleeping!")


def main():
    opt = parse_arguments()

    config.debug_mode = opt.debug
    bot_name = "debug" if config.debug_mode else "tor_archivist"

    build_bot(bot_name, __VERSION__)

    config.archive = config.r.subreddit(
        os.environ.get("ARCHIVE_SUBREDDIT", "ToR_Archive")
    )

    # jumpstart the clock -- allow running immediately after starting.
    config.sleep_until = 0
    if opt.noop:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == "__main__":
    main()
