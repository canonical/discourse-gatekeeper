# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all tests."""

from pathlib import Path
from unittest import mock

import pytest
from git.repo import Repo
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.Requester import Requester

import src
from src import pull_request


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
def fixture_mock_github_repo(mock_pull_request: PullRequest) -> Repository:
    """Create a mock github repository instance."""
    mocked_repo = mock.MagicMock(spec=Repository)
    mocked_repo.create_pull.return_value = mock_pull_request
    mocked_repo.full_name = "test/repository"
    return mocked_repo


@pytest.fixture(name="mock_github")
def fixture_mock_github(mock_github_repo: Repository) -> Github:
    """Create a mock github instance."""
    mocked_github = mock.MagicMock(spec=Github)
    mocked_github.get_repo.return_value = mock_github_repo
    return mocked_github


@pytest.fixture(name="repository_client")
def fixture_repository_client(
    repository: tuple[Repo, Path], mock_github_repo: Repository
) -> pull_request.RepositoryClient:
    """Get repository client."""
    (repo, _) = repository
    return pull_request.RepositoryClient(repository=repo, github_repository=mock_github_repo)


@pytest.fixture(name="patch_create_repository_client")
def fixture_patch_create_repository_client(
    monkeypatch: pytest.MonkeyPatch, repository_client: pull_request.RepositoryClient
) -> None:
    """Patch create_repository_client to return a mocked RepositoryClient."""

    def mock_create_repository_client(access_token: str | None, base_path: Path):
        # to accept keywords as arguments
        del access_token
        del base_path

        return repository_client

    monkeypatch.setattr(src, "create_repository_client", mock_create_repository_client)
