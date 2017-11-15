[![Waffle.io - Ready](https://img.shields.io/waffle/label/TranscribersOfReddit/TranscribersOfReddit/ready.svg?colorB=yellow&label=Available%20Issues)](https://waffle.io/TranscribersOfReddit/TranscribersOfReddit)
[![Waffle.io - In Progress](https://img.shields.io/waffle/label/TranscribersOfReddit/TranscribersOfReddit/in%20progress.svg?colorB=green&label=Issues%20Being%20Worked%20On)](https://waffle.io/TranscribersOfReddit/TranscribersOfReddit)
[![Codacy quality](https://img.shields.io/codacy/grade/978e3984e69f4b00b41fa40f5b947797.svg)](https://www.codacy.com/app/TranscribersOfReddit/ToR_Archivist)
[![Codacy coverage](https://img.shields.io/codacy/coverage/978e3984e69f4b00b41fa40f5b947797.svg)](https://www.codacy.com/app/TranscribersOfReddit/ToR_Archivist)
[![Travis build status](https://img.shields.io/travis/TranscribersOfReddit/ToR_Archivist.svg)](https://travis-ci.org/TranscribersOfReddit/ToR_Archivist)
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
$ git clone https://github.com/GrafeasGroup/tor_archivist.git tor_archivist
$ cd tor_archivist/
$ pip install --process-dependency-links .
```

OR

```
$ pip install --process-dependency-links 'git+https://github.com/GrafeasGroup/tor_archivist.git@master#egg=tor_archivist-0'
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
