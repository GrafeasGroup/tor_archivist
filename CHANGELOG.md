# Changelog

We follow [Semantic Versioning](http://semver.org/) as a way of measuring stability of an update. This
means we will never make a backwards-incompatible change within a major version of the project.

## [0.4.0] -- 2019-06-16

- Adds "No Operator (NOOP) mode" for testing infrastructure automation without reaching out externally
- CTRL-C now responds within 5 seconds

## [0.3.0] -- 2019-06-15

- Embeds `tor_core` as `tor_archivist.core`
- Loop that does nothing when in debug mode

## [0.2.0]

- Split from `tor` into one package per bot
