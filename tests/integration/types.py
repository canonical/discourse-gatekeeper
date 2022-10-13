# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Useful types for integration tests."""

from typing import NamedTuple


class Credentials(NamedTuple):
    """Credentials to login to an application."""

    email: str
    username: str
    password: str
