import logging
import os
import time
from datetime import datetime

from tor_archivist import __version__
from tor_archivist.core.config import config
from tor_archivist.core.helpers import (css_flair, run_until_dead,
                                        subreddit_from_url)
from tor_archivist.core.initialize import build_bot
from tor_archivist.core.strings import reddit_url

##############################
CLEAR_THE_QUEUE_MODE = bool(os.getenv('CLEAR_THE_QUEUE', ''))
##############################

thirty_minutes = 1800  # seconds


def noop(cfg):
    time.sleep(10)
    logging.info('Loop!')


def run(config):
    if not CLEAR_THE_QUEUE_MODE and config.sleep_until >= time.time():
        # This is how we sleep for longer periods, but still respond to
        # CTRL+C quickly: trigger an event loop every minute during wait
        # time.
        time.sleep(60)
        return

    logging.info('Starting archiving of old posts...')
    # TODO the bot will now check ALL posts on the subreddit.
    # when we remove old transcription requests, there aren't too many left.
    # but we should make it stop after a certain amount of time anyway
    # eg. if it encounters a post >36 hours old, it will break the loop

    # TODO we can use .submissions(end=unixtime) apparently
    for post in config.tor.new(limit=1000):

        # [META] - do nothing
        # [UNCLAIMED] - remove
        # [COMPLETED] - remove and x-post to r/tor_archive
        # [IN PROGRESS] - do nothing (should discuss)
        # [DISREGARD] - remove
        flair = post.link_flair_css_class

        # is it a disregard post? Nuke it and move on -- we don't want those
        # sitting around and cluttering up the sub
        if flair == css_flair.disregard:
            post.mod.remove()
            continue

        if flair not in (css_flair.unclaimed, css_flair.completed):
            continue

        # find the original post subreddit
        # take it in lowercase so the config is case insensitive
        post_subreddit = subreddit_from_url(post.url).lower()

        # hours until a post from this subreddit should be archived
        hours = config.archive_time_subreddits.get(
            post_subreddit, config.archive_time_default)

        # time since this post was made
        date = datetime.utcfromtimestamp(post.created_utc)
        seconds = int((datetime.utcnow() - date).total_seconds())

        if CLEAR_THE_QUEUE_MODE:
            post.mod.remove()
        elif seconds > hours * 3600:
            logging.info(
                f'Post "{post.title}" is older than maximum age of {hours} '
                f'hours, removing. '
            )

            post.mod.remove()

        # always process completed posts so we don't have a repeat of the
        # me_irl explosion
        if flair == css_flair.completed:
            logging.info(f'Archiving completed post "{post.title}"...')
            config.archive.submit(
                post.title,
                url=reddit_url.format(post.permalink))
            post.mod.remove()
            logging.info('Post archived!')

    if CLEAR_THE_QUEUE_MODE:
        logging.info('Clear the Queue Mode is engaged! Back we go!')
    else:
        logging.info('Finished archiving - sleeping!')
        config.sleep_until = time.time() + thirty_minutes


def main():
    """
        Console scripts entry point for Archivist Bot
    """
    config.debug_mode = bool(os.environ.get('DEBUG_MODE', False))
    bot_name = 'debug' if config.debug_mode else os.environ.get('BOT_NAME', 'bot_archiver')

    build_bot(bot_name, __version__, full_name='u/transcribot')
    config.archive = config.r.subreddit('ToR_Archive')
    config.sleep_until = 0
    if os.getenv('NOOP_MODE', False):
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == '__main__':
    main()
