# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all tests."""

import typing
from pathlib import Path
from unittest import mock

import pytest
from git.repo import Repo
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.Requester import Requester

import src


@pytest.fixture(name="upstream_repository")
def fixture_upstream_repository(tmp_path: Path) -> tuple[Repo, Path]:
    """Create upstream repository."""
    upstream_path = tmp_path / "upstream"
    upstream_path.mkdir()
    upstream = Repo.init(upstream_path)
    writer = upstream.config_writer()
    writer.set_value("user", "name", "upstream_user")
    writer.set_value("user", "email", "upstream_email")
    writer.release()
    upstream.git.checkout("-b", "main")
    (upstream_path / ".gitkeep").touch()
    upstream.git.add(".")
    upstream.git.commit("-m", "'initial commit'")

    return (upstream, upstream_path)


@pytest.fixture(name="repository")
def fixture_repository(
    upstream_repository: tuple[Repo, Path], tmp_path: Path
) -> tuple[Repo, Path]:
    """Create repository with mocked upstream."""
    (_, upstream_path) = upstream_repository
    repo_path = tmp_path / "mocked"
    repo_path.mkdir()
    repo = Repo.clone_from(url=upstream_path, to_path=repo_path)
    repo.git.checkout("main")
    repo.git.pull()
    return (repo, repo_path)


@pytest.fixture(name="mock_pull_request")
def fixture_mock_pull_request() -> PullRequest:
    """Create mock pull request."""
    mock_requester = mock.MagicMock(spec=Requester)
    return PullRequest(
        requester=mock_requester,
        headers={},
        attributes={"html_url": "test_url"},
        completed=False,
    )


@pytest.fixture(name="mock_github_repo")
def fixture_mock_github_repo(mock_pull_request: PullRequest):
    """Create a mock github repository instance."""
    mocked_repo = mock.MagicMock(spec=Repository)
    mocked_repo.create_pull.return_value = mock_pull_request
    mocked_repo.full_name = "test/repository"
    return mocked_repo


@pytest.fixture(name="mock_github")
def fixture_mock_github(mock_github_repo: Repository):
    """Create a mock github instance."""
    mocked_github = mock.MagicMock(spec=Github)
    mocked_github.get_repo.return_value = mock_github_repo
    return mocked_github


@pytest.fixture(name="patch_get_repository_name")
def fixture_patch_get_repository_name(monkeypatch: pytest.MonkeyPatch):
    """Replace get_repository_name operation to pass."""

    def mock_get_repository_name(remote_url: str):
        return remote_url

    monkeypatch.setattr(src, "get_repository_name", mock_get_repository_name)


@pytest.fixture(name="patch_create_github")
def fixture_patch_create_github(monkeypatch: pytest.MonkeyPatch, mock_github: Github):
    """Replace create_github operation to return a mocked github client."""

    def mock_create_github(access_token: typing.Any):
        del access_token
        return mock_github

    monkeypatch.setattr(src, "create_github", mock_create_github)
