import logging
import os
import time
from datetime import datetime

from tor_archivist import __version__
from tor_archivist.core.config import config
from tor_archivist.core.helpers import (
    css_flair, run_until_dead
)
from tor_archivist.core.initialize import build_bot
from tor_archivist.core.strings import reddit_url

##############################
CLEAR_THE_QUEUE_MODE = bool(os.getenv('CLEAR_THE_QUEUE', ''))
NOOP_MODE = bool(os.getenv('NOOP_MODE', ''))
DEBUG_MODE = bool(os.getenv('DEBUG_MODE', ''))
##############################

thirty_minutes = 1800  # seconds


def find_transcription(post):
    """
    Browse the top level comments of a thread, and return the first one that
    is a transcription. Currently pretty much a copy of its counterpart in
    ToR, which should definitely change later on.

    Because we're only processing posts that u/ToR has already accepted as
    complete, then we don't need to be as firm with the check to verify the
    transcription.

    :param post: the thread to look in.
    :return: the matching comment, or None if it wasn't found.
    """
    post.comments.replace_more(limit=0)

    for comment in post.comments.list():
        if all([
                _ in comment.body for _ in [
                    'www.reddit.com/r/TranscribersOfReddit', '&#32;'
                ]
        ]):
            return comment

    return None


def noop(cfg):
    time.sleep(10)
    logging.info('Loop!')


def run(cfg):
    if not CLEAR_THE_QUEUE_MODE and cfg.sleep_until >= time.time():
        # This is how we sleep for longer periods, but still respond to
        # CTRL+C quickly: trigger an event loop every minute during wait
        # time.
        time.sleep(5)
        return

    logging.info('Starting archiving of old posts...')
    # TODO the bot will now check ALL posts on the subreddit.
    # when we remove old transcription requests, there aren't too many left.
    # but we should make it stop after a certain amount of time anyway
    # eg. if it encounters a post >36 hours old, it will break the loop

    # TODO we can use .submissions(end=unixtime) apparently
    for post in cfg.tor.new(limit=1000):

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

        # the original post that might have been transcribed
        original_post = config.r.submission(url=post.url)

        # find the original post subreddit
        post_subreddit = subreddit_from_url(post.url)

        # hours until a post from this subreddit should be archived
        hours = cfg.archive_time_subreddits.get(
            post_subreddit, cfg.archive_time_default)

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

            # look for the transcription
            transcript = find_transcription(original_post)

            if transcript is not None:
                cfg.archive.submit(
                    post.title,
                    url=reddit_url.format(transcript.permalink))
                logging.info('Post archived!')
            else:
                logging.info('Could not find the transcript - won\'t archive.')

            post.mod.remove()

    if CLEAR_THE_QUEUE_MODE:
        logging.info('Clear the Queue Mode is engaged! Back we go!')
    else:
        logging.info('Finished archiving - sleeping!')
        cfg.sleep_until = time.time() + thirty_minutes


def main():
    config.debug_mode = DEBUG_MODE
    bot_name = 'debug' if config.debug_mode else os.getenv('BOT_NAME', 'bot_archiver')

    build_bot(bot_name, __version__, full_name='u/transcribot')
    config.archive = config.r.subreddit('ToR_Archive')
    config.sleep_until = 0
    if NOOP_MODE:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == '__main__':
    main()
