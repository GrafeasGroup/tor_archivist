import logging
from datetime import datetime

from tor_core.config import config
from tor_core.helpers import css_flair
from tor_core.helpers import run_until_dead
from tor_core.helpers import subreddit_from_url
from tor_core.initialize import build_bot
from tor_core.strings import reddit_url

from tor_archivist import __version__


def run(config):
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

        if flair not in (css_flair.unclaimed, css_flair.completed):
            continue

        # is it a disregard post? Nuke it and move on -- we don't want those
        # sitting around and cluttering up the sub
        if flair == css_flair.disregard:
            post.mod.remove()
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

        if seconds > hours * 3600:
            logging.info(
                'Post "{}" is older than maximum age of {} hours, removing.'.format(
                    post.title, hours)
            )

            post.mod.remove()

        # copy completed posts to archive subreddit
        if flair == css_flair.completed:
            logging.info('Archiving completed post "{}"...'.format(post.title))
            config.archive.submit(
                post.title,
                url=reddit_url.format(post.permalink))
            logging.info('Post archived!')


def main():
    """
        Console scripts entry point for Archivist Bot
    """
    
    build_bot('bot_archiver',
              __version__,
              full_name='u/transcribot',
              log_name='archiver.log')
    config.archive = config.r.subreddit('ToR_Archive')
    run_until_dead(run)

if __name__ == '__main__':
    main()
