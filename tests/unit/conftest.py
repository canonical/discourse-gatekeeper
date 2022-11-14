# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all unit tests."""

# pylint: disable=redefined-outer-name

import pytest

from src.discourse import Discourse


@pytest.fixture(scope="module")
def base_path():
    """Get the base path for discourse."""
    return "http://discourse"


@pytest.fixture(scope="module")
def discourse(base_path: str):
    """Get the discourse client."""
    return Discourse(base_path=base_path, api_username="", api_key="", category_id=0)
