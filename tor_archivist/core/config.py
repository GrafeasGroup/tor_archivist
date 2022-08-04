import os
from typing import Optional

import pkg_resources
from blossom_wrapper import BlossomAPI

from praw import Reddit
from praw.models import Subreddit

from tor_archivist import ARCHIVING_RUN_STEPS

# Load configuration regardless of if bugsnag is setup correctly
try:
    import bugsnag
except ImportError:
    # If loading from setup.py or bugsnag isn't installed, we
    # don't want to bomb out completely
    bugsnag = None

_missing = object()


# @see https://stackoverflow.com/a/17487613/1236035
class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.
    """

    # implementation detail: this property is implemented as non-data
    # descriptor. non-data descriptors are only invoked if there is no
    # entry with the same name in the instance's __dict__. this allows
    # us to completely get rid of the access function call overhead. If
    # one choses to invoke __get__ by hand the property will still work
    # as expected because the lookup logic is replicated in __get__ for
    # manual invocation.

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, _type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


class Config(object):
    """
    A singleton object for checking global configuration from
    anywhere in the application
    """

    # API keys for later overwriting based on contents of filesystem
    bugsnag_api_key = None

    debug_mode = False

    # Name of the bot
    name: Optional[str] = None
    bot_version: str = "0.0.0"  # this should get overwritten by the bot process

    # to be overwritten later with blossom-wrapper
    blossom: Optional[BlossomAPI] = None
    # to be overwritten with the Reddit connection
    reddit: Optional[Reddit] = None
    # the subreddit of the archives. Default is r/ToR_Archive
    archive: Optional[Subreddit] = None
    # the main subreddit. Default is r/TranscribersOfReddit
    tor: Optional[Subreddit] = None

    # the current step number for the archiving runs
    # we can skip some steps if we want faster report syncing
    archive_run_step = ARCHIVING_RUN_STEPS


try:
    Config.bugsnag_api_key = open("bugsnag.key").readline().strip()
except OSError:
    Config.bugsnag_api_key = os.environ.get("BUGSNAG_API_KEY", None)

if bugsnag and Config.bugsnag_api_key:
    bugsnag.configure(
        api_key=Config.bugsnag_api_key,
        app_version=pkg_resources.get_distribution("tor_archivist").version,
    )

# ----- Compatibility -----
config = Config()
