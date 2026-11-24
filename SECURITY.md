# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 2.x | Yes |
| Earlier, unversioned script | No |

## Reporting a vulnerability

Use the private vulnerability reporting option on the repository's GitHub Security tab if it is
available. Otherwise, open an issue asking for a private contact, without including exploit
details. This is a personal project, so responses are best effort and no response time is promised.

## Scope and threat model

This is a local command-line tool. It has no network access, authentication, or runtime
dependencies. Its inputs are command-line flags and an optional SQLite file path chosen by the
person running it. Do not point it at a database file you do not trust.

The `random` module is intentionally used for simulation and must not be reused for security
purposes. Seeds are not secrets.
