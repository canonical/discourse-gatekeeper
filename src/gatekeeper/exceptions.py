# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions for uploading docs to charmhub."""


class BaseError(Exception):
    """All raised exceptions inherit from this one."""


class InputError(BaseError):
    """A problem with the user input occurred."""


class ServerError(BaseError):
    """A problem with the server storing the documentation occurred."""


class PagePermissionError(BaseError):
    """A required permission is not available on a page."""


class DiscourseError(BaseError):
    """Parent exception for all Discourse errors."""


class NavigationTableParseError(BaseError):
    """A problem with the navigation table parsing occurred."""


class ReconcilliationError(BaseError):
    """A problem with the reconcilliation occurred."""


class ActionError(BaseError):
    """A problem with the taking an action occurred."""


class MigrationError(BaseError):
    """A problem with migration occurred."""


class RepositoryClientError(BaseError):
    """A problem with git repository client occurred."""


class RepositoryFileNotFoundError(BaseError):
    """A problem retrieving a file from a git repository occurred."""


class RepositoryTagNotFoundError(BaseError):
    """A problem retrieving a tag from a git repository occurred."""


class TaggingNotAllowedError(BaseError):
    """The commit cannot be tagged as it is outside of the main."""


class ContentError(BaseError):
    """A problem with the content occurred."""
