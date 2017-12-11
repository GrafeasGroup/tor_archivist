import logging
import os
from datetime import datetime
from time import sleep

from tor_core.config import config
from tor_core.helpers import css_flair
from tor_core.helpers import run_until_dead
from tor_core.initialize import build_bot
from tor_core.strings import reddit_url

from tor_archivist import __version__


def find_transcription(post):
    """
    Browse the top level comments of a thread, and return the first one that
    is a transcription. Currently pretty much a copy of its counterpart in
    ToR, which should definitely change later on.

    :param post: the thread to look in.
    :return: the matching comment, or None if it wasn't found.
    """
    post.comments.replace_more(limit=0)

    for comment in post.comments.list():
        if 'www.reddit.com/r/TranscribersOfReddit' in comment.body:
            return comment

    return None


def run(config):
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

        # the original post that might have been transcribed
        original_post = config.r.submission(url=post.url)

        # find the original post subreddit
        # take it in lowercase so the config is case insensitive
        post_subreddit = original_post.subreddit

        # hours until a post from this subreddit should be archived
        hours = config.archive_time_subreddits.get(
            post_subreddit, config.archive_time_default)

        # time since this post was made
        date = datetime.utcfromtimestamp(post.created_utc)
        seconds = int((datetime.utcnow() - date).total_seconds())

        if seconds > hours * 3600:
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
                config.archive.submit(
                    post.title,
                    url=reddit_url.format(transcript.permalink))
                logging.info('Post archived!')
            else:
                logging.info('Could not find the transcript - won\'t archive.')

            post.mod.remove()

    logging.info('Finished archiving - sleeping!')
    sleep(30 * 60)  # 30 minutes


def main():
    """
        Console scripts entry point for Archivist Bot
    """
    config.debug_mode = bool(os.environ.get('DEBUG_MODE', False))
    bot_name = 'debug' if config.debug_mode else os.environ.get('BOT_NAME', 'bot_archiver')

    build_bot(bot_name, __version__, full_name='u/transcribot', log_name='archiver.log')
    config.archive = config.r.subreddit('ToR_Archive')
    run_until_dead(run)


if __name__ == '__main__':
    main()
