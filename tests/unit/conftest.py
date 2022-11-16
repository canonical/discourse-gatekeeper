# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all unit tests."""

# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest

from src.discourse import Discourse


@pytest.fixture(scope="module")
def base_path():
    """Get the base path for discourse."""
    return "http://discourse"


@pytest.fixture()
def discourse(base_path: str):
    """Get the discourse client."""
    return Discourse(base_path=base_path, api_username="", api_key="", category_id=0)


@pytest.fixture()
def index_file(tmp_path: Path):
    """Create index file."""
    docs_folder = tmp_path / "docs"
    docs_folder.mkdir()
    index_file = docs_folder / "index.md"
    content = "content 1"
    index_file.write_text(content, encoding="utf-8")
    return content
