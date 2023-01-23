# Changelog

## [Unreleased]

### Added

- Check to ensure that a topic URL resolves on discourse after allowing for any
  redirects. This also relaxes the URL checking to be on the URL after any
  redirects rather than before letting topic URLs pass that do not include the
  slug or do not include the topic id as long as the URL after redirects is
  valid.

## [v0.2.1] - 2023-01-20

### Fixed

- Migration now correctly handles that the git checkout on GitHub actions runs
  in detached head mode, the migration failed before due to not being able to
  create a new branch from detached head mode
- Only files in the `docs` folder are now added to the migration PR
- The migration PR is now created with a branch from the default branch merging
  back into the default branch, previously the branch was from the branch the
  action was running on back into that branch

## [v0.2.0] - 2023-01-13

### Added

- Topics are now created unlisted on discourse
- Runs on a charm with existing documentation and without the `docs` folder now
  results in a PR being created to migrate the docs to the repository

## [v0.1.1] - 2022-12-13

### Fixed

- Resolve bug where the presence of a topic on the server was not checked

### Fixed

- Allow redirects for topic retrieval which is useful if the slug is
  incorrectly or not defined

## [v0.1.0] - 2022-12-07

### Added

- Copying files from source to discourse
- Dry run mode to see changes that would occur without executing them
- Option to skip deleting topics from discourse

[//]: # "Release links"
[0.1.1]: https://github.com/canonical/upload-charm-docs/releases/v0.1.1
[0.1.0]: https://github.com/canonical/upload-charm-docs/releases/v0.1.0
