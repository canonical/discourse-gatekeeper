# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions for uploading docs to charmhub."""


class BaseError(Exception):
    """All raised exceptions inherit from this one."""


class InputError(BaseError):
    """A problem with the user input occurred."""


class ServerError(BaseError):
    """A problem with the server storing the documentation occurred."""


class DiscourseError(BaseError):
    """Parent exception for all Discourse errors."""


class NavigationTableParseError(BaseError):
    """A problem with the navigation table parsing occurred."""


class ReconcilliationError(BaseError):
    """A problem with the reconcilliation occurred."""


class ActionError(BaseError):
    """A problem with the taking an action occurred."""


class InvalidTableRowError(BaseError):
    """A problematic table row is encountered."""


class MigrationError(BaseError):
    """A problem with migration occurred."""


class GitError(BaseError):
    """A problem with git occurred."""
