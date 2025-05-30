# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all unit tests."""

from pathlib import Path
from unittest import mock

import pytest
import requests

from gatekeeper import Clients, constants, repository
from gatekeeper.discourse import Discourse

from . import helpers


@pytest.fixture(scope="module", name="host")
def fixture_host() -> str:
    """Get the base path for discourse."""
    return helpers.get_discourse_host()


@pytest.fixture(name="discourse")
def fixture_discourse(host: str) -> Discourse:
    """Get the discourse client."""
    return Discourse(host=host, api_username="", api_key="", category_id=0)


@pytest.fixture(name="discourse_mocked_get_requests_session")
def fixture_discourse_mocked_get_requests_session(
    discourse: Discourse, monkeypatch: pytest.MonkeyPatch
) -> Discourse:
    """Get the mocked get_session."""
    # Have to access protected attributes to be able to mock them for tests
    # pylint: disable=protected-access
    mock_get_requests_session = mock.MagicMock(spec=discourse._get_requests_session)
    mocked_session = mock.MagicMock(spec=requests.Session)
    mock_get_requests_session.return_value = mocked_session
    mocked_get_response = mock.MagicMock(spec=requests.Response)
    mocked_session.get.return_value = mocked_get_response
    mocked_head_response = mock.MagicMock(spec=requests.Response)
    mocked_session.head.return_value = mocked_head_response
    monkeypatch.setattr(discourse, "_get_requests_session", mock_get_requests_session)
    return discourse


@pytest.fixture(name="topic_url")
def fixture_topic_url(discourse_mocked_get_requests_session: Discourse) -> str:
    """Get the base path for discourse."""
    url = helpers.get_discourse_topic_url()
    discourse = discourse_mocked_get_requests_session
    # Have to access protected attributes to be able to mock them for tests
    # pylint: disable=protected-access
    # mypy complains that _get_requests_session has no attribute ..., it is actually mocked
    discourse._get_requests_session.return_value.head.return_value.url = url  # type: ignore
    return url


@pytest.fixture()
def index_file_content(tmp_path: Path) -> str:
    """Create index file."""
    docs_directory = tmp_path / constants.DOCUMENTATION_FOLDER_NAME
    docs_directory.mkdir()
    index_file = docs_directory / constants.DOCUMENTATION_INDEX_FILENAME
    content = "content 1"
    index_file.write_text(content, encoding="utf-8")
    return content


@pytest.fixture()
def mocked_clients(repository_client: repository.Client, host: str):
    """Create index file."""
    mocked_discourse = mock.MagicMock(spec=Discourse)
    mocked_discourse.host = host
    return Clients(discourse=mocked_discourse, repository=repository_client)
