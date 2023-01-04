# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all unit tests."""

# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest
from git.repo import Repo
from github.Repository import Repository

from src import index, pull_request
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
def repository_client(repository: tuple[Repo, Path], mock_github_repo: Repository):
    """Get repository client."""
    (repo, _) = repository
    return pull_request.RepositoryClient(repository=repo, github_repository=mock_github_repo)
