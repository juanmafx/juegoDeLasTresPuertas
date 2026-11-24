# Release Notes: 3.0.1

Version 3.0.1 is a documentation release. It does not change the behaviour of any
implementation. Only the version reported by `--version` changes, from 3.0.0 to 3.0.1, in
Python, Java, PHP and C.

## Changes

- The changelog marks 3.0.0 as released on 2026-11-24.
- The changelog no longer says that the removed `MontyHall.py` remains in Git history.
- The security audit notes that the public history was rewritten on 2026-11-24, so commits
  earlier than 2026 are no longer in any branch or tag. Anything that was ever published in the
  old history should still be treated as compromised.

## Upgrading

No action is needed when upgrading from 3.0.0. See the 3.0.0 entry in
[CHANGELOG.md](CHANGELOG.md) for the breaking changes of the decision lab release.

## Verification

The test suites of all four implementations were run for this release. The CI workflows run on
GitHub Actions for every push to `master`.
