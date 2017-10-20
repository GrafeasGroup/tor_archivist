[![Waffle.io - Columns and their card count](https://badge.waffle.io/TranscribersOfReddit/TranscribersOfReddit.svg?columns=all)](http://waffle.io/TranscribersOfReddit/TranscribersOfReddit)
[![BugSnag](https://img.shields.io/badge/errors--hosted--by-Bugsnag-blue.svg)](https://www.bugsnag.com/open-source/)

# Archiver Bot - Transcribers Of Reddit

The officially licensed archivist for /r/TranscribersOfReddit!

This is the source code for the bot that handles archiving completed or stale
posts from the front page of /r/TranscribersOfReddit, a community dedicated
to transcribing images, audio, and video. It acts under the username `/u/ToR_archivist`.

## Resources

- Redis (tracking completed posts and queue system)
- Reddit API keys

> **NOTE:**
>
> This code is not complete. The praw.ini file is required to run the bots and
> contains information such as the useragents and certain secrets. It is built
> for Python 3.6.

## Installation

Make sure you have an [up-to-date copy of pip installed](https://pip.pypa.io/en/stable/installing/) and Python 3.6.

```
$ git clone https://github.com/TranscribersOfReddit/ToR_Archivist.git tor_archivist
$ cd tor_archivist/
$ pip install --process-dependency-links .
```

OR

```
$ pip install --process-dependency-links 'git+https://github.com/TranscribersOfReddit/ToR_Archivist.git@master#egg=tor_archivist-0'
```

## High-level functionality

Monitoring daemon (via [/r/TranscribersOfReddit/new](https://www.reddit.com/r/TranscribersOfReddit/new) feed):

- For each completed or unclaimed post:
  - Retrieve what subreddit contained the original linked post
  - If the post is older than the configured amount of time for target subreddit:
    - If completed:
      - Link to post in [/r/ToR_Archive](https://www.reddit.com/r/ToR_Archive)
    - Remove the post

## Running Archiver Bot

```
$ tor-archivist
# => [daemon mode + logging]
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.
