[![Stories in Ready](https://badge.waffle.io/TranscribersOfReddit/ToR_Archivist.png?label=ready&title=Ready)](http://waffle.io/TranscribersOfReddit/ToR_Archivist)
[![BugSnag](https://img.shields.io/badge/errors--hosted--by-Bugsnag-blue.svg)](https://www.bugsnag.com/open-source/)

# Archiver Bot - Transcribers Of Reddit

The code for TranscribersOfReddit's official licensed archivist!
This is the source code for Archiver Bot (`/u/ToR_archivist`), the officially
licensed archivist for /r/TranscribersOfReddit (ToR). It forms one part of the
team that assists in the running or /r/TranscribersOfReddit (ToR), which is
privileged to have the incredibly important job of organizing crowd-sourced
transcriptions of images, video, and audio.

As a whole, the ToR bots are designed to be as light on local resources as they
can be, though there are some external requirements.

- Redis (tracking completed posts and queue system)

> **NOTE:**
>
> This code is not complete. The praw.ini file is required to run the bots and
> contains information such as the useragents and certain secrets. It is built
> for Python 3.6.

## Installation

```
$ git clone https://github.com/TranscribersOfReddit/ToR_Archivist.git tor-archivist
$ pip install --process-dependency-links tor-archivist/
```

OR

```
$ pip install --process-dependency-links 'git+https://github.com/TranscribersOfReddit/ToR_Archivist.git@master#egg=tor_archivist'
```

## High-level functionality

Monitoring daemon (via subreddit's /new feed):

- For each completed or unclaimed post:
   - Retrieve in which subreddit the original post was made
   - If the post is older than the configured amount of time for this subreddit:
     - Remove the post
     - If it was completed, make the same post in the archive subreddit

## Running Archiver Bot

```
$ tor-archivist
# => [daemon mode + logging]
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.
