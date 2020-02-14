import logging
import os
import time
import dotenv
from datetime import datetime

from tor_archivist import __version__
from tor_archivist.core.config import config
from tor_archivist.core.helpers import (
    css_flair, run_until_dead, subreddit_from_url
)
from tor_archivist.core.initialize import build_bot
from tor_archivist.core.strings import reddit_url
from tor_archivist.core.reddit_ids import is_removed
from tor_archivist.core.blossom import BlossomAPI

##############################
CLEAR_THE_QUEUE_MODE = bool(os.getenv('CLEAR_THE_QUEUE', ''))
NOOP_MODE = bool(os.getenv('NOOP_MODE', ''))
DEBUG_MODE = bool(os.getenv('DEBUG_MODE', ''))
##############################

thirty_minutes = 1800  # seconds

dotenv.load_dotenv()

b_api = BlossomAPI(
    email=os.environ.get('TOR_OCR_EMAIL'), 
    password=os.environ.get('TOR_OCR_PASSWORD'), 
    api_key=os.environ.get('TOR_OCR_BLOSSOM_API_KEY'), 
    api_base_url=os.environ.get('TOR_OCR_BLOSSOM_API_BASE_URL'),
    login_url=os.environ.get('TOR_OCR_BLOSSOM_API_LOGIN_URL')
)

def noop(cfg):
    time.sleep(10)
    logging.info('Loop!')


def run(cfg):
    if not CLEAR_THE_QUEUE_MODE and cfg.sleep_until >= time.time():
        # TODO: if ctq is active, send ctq query parameter to expired endpoint
        # This is how we sleep for longer periods, but still respond to
        # CTRL+C quickly: trigger an event loop every minute during wait
        # time.
        time.sleep(5)
        return

    logging.info('Starting archiving of old posts...')


    if unarchived_submissions := b_api.get("/submission/unarchived/").json():
        if unarchived_submissions.get('data'):
            for submission in unarchived_submissions['data']:

                post_subreddit = subreddit_from_url(submission['url'])

                # the original post from r/ToR that might have been transcribed
                reddit_post = config.r.submission(id=submission['submission_id'])

                # unccomment the below line in prodution to remove original r/ToR post
                # reddit_post.mod.remove()

                transcription = b_api.get(
                    f"/transcription/search/?submission_id={submission['submission_id']}"
                ).json()
                if transcription.get('data'):
                    transcription = transcription['data'][0]
                    b_api.patch(f"/submission/{submission['id']}/", {'archived': True})

                    # for now we are not going to backup the ToR archive url, but we can 
                    # address later
                    if transcription['url'] != None:
                        cfg.archive.submit(
                            reddit_post.title,
                            url=transcription['url']
                        )
                        logging.info('Post archived!')
                else:
                    logging.info(
                        f'could not find transcription for post id'
                        f" {submission['submission_id']}"
                    )
        else:
            logging.debug('no unarchived submissions')

    if expired_submissions := b_api.get("/submission/expired/").json():
        if expired_submissions.get('data'):
            for submission in expired_submissions['data']:
                # the original post from r/ToR that might have been transcribed
                reddit_post = config.r.submission(id=submission['submission_id'])
                # unccomment the below line in prodution to remove original r/ToR post
                # reddit_post.mod.remove()
                b_api.patch(f"/submission/{submission['id']}/", {'archived': True} )
        else:
            logging.debug('no expired submissions')

    if CLEAR_THE_QUEUE_MODE:
        logging.info('Clear the Queue Mode is engaged! Loop!')
    else:
        logging.info('Finished archiving - sleeping!')
        cfg.sleep_until = time.time() + thirty_minutes


def main():
    config.debug_mode = DEBUG_MODE
    bot_name = 'debug' if config.debug_mode else os.getenv('BOT_NAME', 'bot_archiver')

    build_bot(bot_name, __version__, full_name='u/transcribot')
    
    config.archive = config.r.subreddit('tor_testing_ground')

    # change config.archive to tor_archive in production
    # config.archive = config.r.subreddit('tor_archive')
    config.sleep_until = 0
    if NOOP_MODE:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == '__main__':
    main()
