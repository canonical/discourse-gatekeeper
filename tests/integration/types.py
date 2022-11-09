# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Useful types for integration tests."""

from typing import NamedTuple


class Credentials(NamedTuple):
    """Credentials to login to an application."""

    email: str
    username: str
    password: str
