# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions for uploading docs to charmhub."""


class BaseException(Exception):
    """All raised exceptions inherit from this one."""


class InputError(BaseException):
    """A problem with the user input occurred."""


class ServerError(BaseException):
    """A problem with the server storing the documentation occurred."""


class DiscourseError(BaseException):
    """Parent exception for all Discourse errors."""
