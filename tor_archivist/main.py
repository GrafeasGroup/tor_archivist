import logging
import os
import time
from typing import Any, Dict

import dotenv
import pkg_resources
from blossom_wrapper import BlossomStatus

from tor_archivist.core.config import config, Config
from tor_archivist.core.helpers import (
    run_until_dead, get_id_from_url
)
from tor_archivist.core.initialize import build_bot
from tor_archivist.core.strings import reddit_url

##############################
CLEAR_THE_QUEUE_MODE = bool(os.getenv('CLEAR_THE_QUEUE', ''))
NOOP_MODE = bool(os.getenv('NOOP_MODE', ''))
DEBUG_MODE = bool(os.getenv('DEBUG_MODE', ''))
##############################

thirty_minutes = 1800  # seconds

dotenv.load_dotenv()


def noop(*args: Any) -> None:
    time.sleep(10)
    logging.info('Loop!')


def process_expired_posts(cfg: Config) -> None:
    response = cfg.blossom.get_expired_submissions()

    if response.status != BlossomStatus.ok:
        logging.warning("Received bad response from Blossom. Cannot process.")
        return

    if hasattr(response, "data"):
        for submission in response.data:
            cfg.r.submission(url=submission['tor_url']).mod.remove()
            cfg.blossom.archive_submission(submission_id=submission['id'])
            logging.info(
                f"Archived expired submission {submission['id']} - original_id"
                f" {submission['original_id']}"
            )


def get_human_transcription(cfg: Config, submission: Dict) -> Dict:
    response = cfg.blossom.get("transcription/search/", params={"submission_id": submission["id"]})
    for transcription in response.json():
        if int(get_id_from_url(transcription['author'])) == config.transcribot['id']:
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
            reddit_post = cfg.r.submission(url=submission['tor_url'])
            reddit_post.mod.remove()
            cfg.blossom.archive_submission(submission_id=submission['id'])

            transcription = get_human_transcription(cfg, submission)

            if not transcription:
                logging.warning(
                    f"Received completed post ID {submission['id']} with no valid"
                    f" transcriptions."
                )
                # This means that we _should not_ make a post on r/ToR_Archive
                # because there's no transcription to link to.
                continue

            if not transcription.get('url'):
                logging.warning(
                    f"Transcription {transcription['id']} does not have a URL"
                    f" - skipping."
                )
                continue

            cfg.archive.submit(
                reddit_post.title,
                url=reddit_url.format(transcription['url'])
            )
            logging.info(
                f"Submission {submission['id']} - original_id"
                f" {submission['original_id']} - archived!"
            )


def run(cfg: Config) -> None:
    if not CLEAR_THE_QUEUE_MODE and cfg.sleep_until >= time.time():
        # TODO: if ctq is active, send ctq query parameter to expired endpoint
        # This is how we sleep for longer periods, but still respond to
        # CTRL+C quickly: trigger an event loop every few seconds during wait
        # time.
        time.sleep(5)
        return

    logging.info('Starting archiving of old posts...')

    archive_completed_posts(cfg)

    process_expired_posts(cfg)

    if CLEAR_THE_QUEUE_MODE:
        logging.info('Clear the Queue Mode is engaged! Loop!')
    else:
        logging.info('Finished archiving - sleeping!')
        cfg.sleep_until = time.time() + thirty_minutes


def main():
    config.debug_mode = DEBUG_MODE
    bot_name = 'debug' if config.debug_mode else os.getenv('BOT_NAME', 'bot_archiver')

    build_bot(bot_name, pkg_resources.get_distribution('tor_archivist').version)

    config.archive = config.r.subreddit(os.environ.get('ARCHIVE_SUBREDDIT', 'ToR_Archive'))

    # jumpstart the clock -- allow running immediately after starting.
    config.sleep_until = 0
    if NOOP_MODE:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == '__main__':
    main()
