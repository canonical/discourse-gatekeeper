# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all unit tests."""

# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest
from git.repo import Repo

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
def upstream_repository(tmp_path: Path) -> tuple[Repo, Path]:
    """Create upstream repository."""
    upstream_path = tmp_path / "upstream"
    upstream_path.mkdir()
    upstream = Repo.init(upstream_path)
    upstream.git.checkout("-b", "main")
    (upstream_path / "index.md").touch()
    upstream.git.add(".")
    upstream.git.commit("-m", "'initial commit'")

    return (upstream, upstream_path)


@pytest.fixture()
def temp_repository(upstream_repository: tuple[Repo, Path], tmp_path: Path) -> tuple[Repo, Path]:
    """Create temporary repository."""
    (_, upstream_path) = upstream_repository
    repo_path = tmp_path / "temp"
    repo_path.mkdir()
    repo = Repo.clone_from(url=upstream_path, to_path=repo_path)
    return (repo, repo_path)


@pytest.fixture()
def repository(upstream_repository: tuple[Repo, Path], tmp_path: Path) -> tuple[Repo, Path]:
    """Create repository with mocked upstream."""
    (_, upstream_path) = upstream_repository
    repo_path = tmp_path / "mocked"
    repo_path.mkdir()
    repo = Repo.clone_from(url=upstream_path, to_path=repo_path)
    return (repo, repo_path)
