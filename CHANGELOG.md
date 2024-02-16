# Changelog

## [Unreleased]

- Added a formatted representation of the UpdatePageAction dataclass for more
  human-readable output.

## [v0.8.2] - 2024-02-16

### Fixed

- Removed soft-conflict ignore button. `discourse-ahead-ok` tag, which was used
  to indicate changes between discourse and git should no longer be used. Has been
  removed, with tests updated to reflect this.

## [v0.8.1] - 2024-01-18

### Fixed

- Migration error where discourse is in-line with the default branch but the
  base content tag is behind. This no longer attempts migration and now also
  moves the tag to the latest commit on the default branch.

## [v0.8.0] - 2023-11-30

### Added

- Support for migrating the navigation table to the contents index
- Checks that external references on the contents index return a 2XX response to
  HEAD requests

### Fixed

- Whitespace buildup between generated and input content

## [v0.7.0] - 2023-10-09

### Added

- Support for defining a contents index in the `index.md` file.
- Support for hidden items on the contentx index.
- Support for external items on the contents index
- Automatically moving the `discourse-gatekeeper/content` tag when the
  documentation is up to date with discourse

### Fixed

- Navigation table not getting removed if the contents was hidden using the
  `[details=...]...[/details]` tag.
- No longer use empty values from `INPUT_COMMIT_SHA` instead of reading the
  event/ environment
- Removing leading and trailing whitespace in base content for comparison
- Correct failing pre-flight checks due to shallowly checked out repos

## [v0.6.0] - 2023-07-07

### Added

- Raising PRs with community contributions on discourse
- Signing commits if required by a repository

### Changed

- Conflict detection logic no longer uses git to merge for page conflicts.
  Instead any differences between discourse and the feature branch on a specific
  page lead to a failed run.

### Fixed

- Improved logging of conflicts

## [v0.5.0] - 2023-04-18

### Changed

- Removed `base_branch` input.

### Fixed

- Add support for handling tags that are directly linked to a commit which
  resulted in a failure before.

## [v0.4.0] - 2023-04-13

### Changed

- The base for the content comparison is no longer based on using a branch.
  Instead, the action will look for a tag with a default value of
  `upload-charm-docs/base-content` which can be changed using the
  `base_tag_name` input. This ensures that the comparison can be made even if
  the action is run on the default branch. The action will now fail if the
  `base_tag_name` is not found on the repository.
- On a successful run in reconciliation mode with dry run not enabled, the
  action will automatically add the `base_tag_name` tag to the commit on which
  it was run.
- The `base_branch` input has been deprecated and will be removed in a future
  release. It is no longer in use.

## [v0.3.0] - 2023-04-04

### Changed

- The action now checks for conflicts with any edits directly on discourse and
  will fail the content update if there are conflicts. The git merge algorithm
  is used to merge content where there are no conflicts with the new content in
  git and the changed content on discourse. The `base_branch` input can be used
  to set the branch that contains the content for the base of the comparison for
  conflicts. It should be the branch targeted by pull requests and from which
  releases are usually done. This input is optional and defaults to the default
  branch of the repository.
- The `github_token` input has been changed to be required as it is now also
  required during reconciliation to retrieve the content that was last pushed
  from git to discousrse as a base for checking for content conflicts and
  merging content.

## [v0.2.3] - 2023-01-25

### Added

- Check to ensure that a topic URL resolves on discourse after allowing for any
  redirects.

### Changed

- URL checks are now after allowing for any discourse redirects rather than
  before letting topic URLs pass that do not include the slug or do not include
  the topic id as long as the URL after redirects is valid.
- The check for whether the current branch clashes with the branch being created
  has been removed. This is no longer required because the migration branch is
  now from the default branch and there is an existing check that looks for any
  clashes with existing branches.
- The action no longer goes back to detached head mode after completing git
  operations since the action now runs in a temporary directory meaning that no
  changes persist beyond the action completing.

### Fixed

- Bug where the action required environment variables that aren't available on
  all supported triggers.

## [v0.2.2] - 2023-01-23

### Fixed

- Name clashes during migration for checkouts when a file or directory has the
  same name as the branch being checked out

### Changed

- The action now operates in a temporary directory that is a copy of the
  directory the action was called on. Using a temporary directory ensures that
  any operations of the action, such as git operations, do not change the state
  of the files and directories any following steps receive.

## [v0.2.1] - 2023-01-20

### Fixed

- Migration now correctly handles that the git checkout on GitHub actions runs
  in detached head mode, the migration failed before due to not being able to
  create a new branch from detached head mode
- Only files in the `docs` directory are now added to the migration PR
- The migration PR is now created with a branch from the default branch merging
  back into the default branch, previously the branch was from the branch the
  action was running on back into that branch

## [v0.2.0] - 2023-01-13

### Added

- Topics are now created unlisted on discourse
- Runs on a charm with existing documentation and without the `docs` directory
  now results in a PR being created to migrate the docs to the repository

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
