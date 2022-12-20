# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all unit tests."""

# pylint: disable=redefined-outer-name

from pathlib import Path
from unittest import mock

import pytest
from github.PullRequest import PullRequest
from github.Requester import Requester

from src import index
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
def index_file_content(tmp_path: Path):
    """Create index file."""
    docs_directory = tmp_path / index.DOCUMENTATION_FOLDER_NAME
    docs_directory.mkdir()
    index_file = docs_directory / index.DOCUMENTATION_INDEX_FILENAME
    content = "content 1"
    index_file.write_text(content, encoding="utf-8")
    return content


@pytest.fixture()
def mock_pull_request() -> PullRequest:
    """Create mock pull request."""
    mock_requester = mock.MagicMock(spec=Requester)
    return PullRequest(
        requester=mock_requester,
        headers={},
        attributes={"url": "test_url"},
        completed=False,
    )
