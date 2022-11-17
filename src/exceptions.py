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
