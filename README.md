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

### From release

Given a release in <https://github.com/GrafeasGroup/tor_archivist/releases>, download the attached `.tar.gz` file for your platform/architecture and `pip install` it directly like so:

```sh
$ pip install ./path/to/tor_archivist-1.0.0-linux-x86_64.tar.gz
```

### From source

Make sure you have an [up-to-date copy of poetry installed](https://github.com/sdispater/poetry#installation) and at least Python 3.6.

```sh
$ git clone https://github.com/GrafeasGroup/tor_archivist.git tor_archivist
$ cd tor_archivist/
$ poetry install
```

## High-level functionality

Monitoring daemon (via [/r/TranscribersOfReddit/new](https://www.reddit.com/r/TranscribersOfReddit/new) feed):

- For each completed or unclaimed post:
  - Retrieve what subreddit contained the original linked post
  - If the post is older than the configured amount of time for target subreddit:
    - If completed:
      - Link to post in [/r/ToR_Archive](https://www.reddit.com/r/ToR_Archive)
    - Remove the post

## Build

To build the package from source, start in the base of the repository and run:

```sh
$ poetry build
```

When building is complete, upload the `.whl` file in the `dist/` directory that was just created as part of the GitHub release.

## Usage

```sh
$ tor-archivist
# => [daemon mode + logging]
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.
