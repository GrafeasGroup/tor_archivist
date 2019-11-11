# Changelog

We follow [Semantic Versioning](http://semver.org/) as a way of measuring stability of an update. This
means we will never make a backwards-incompatible change within a major version of the project.

## [UNRELEASED]

- Fixes error thrown if trying to clean a reddit id that has already been cleaned

## [0.7.0] -- 2019-11-10

- Automatically removes posts that appear to have been removed by partner subs

## [0.6.0] -- 2019-11-10

- Switches to Poetry toolchain for python module development and packaging

## [0.5.1] -- 2019-09-20

- FIX: Type mismatch. Expected string, got Subreddit object

## [0.5.0] -- 2019-09-20

- Link to the transcription comment directly in archive posts, rather than to the original post itself.

## [0.4.1] -- 2019-06-16

- FIX: unneeded kwargs removed for log file name, but not everywhere

## [0.4.0] -- 2019-06-16

- Adds "No Operator (NOOP) mode" for testing infrastructure automation without reaching out externally
- CTRL-C now responds within 5 seconds

## [0.3.0] -- 2019-06-15

- Embeds `tor_core` as `tor_archivist.core`
- Loop that does nothing when in debug mode

## [0.2.0]

- Split from `tor` into one package per bot
