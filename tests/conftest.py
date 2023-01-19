# Copyright 2023 Canonical Ltd.
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


@pytest.fixture(name="upstream_repository_path")
def fixture_upstream_repository_path(tmp_path: Path) -> Path:
    """Create a path for upstream repository."""
    upstream_path = tmp_path / "upstream"
    upstream_path.mkdir()
    return upstream_path


@pytest.fixture(name="default_branch")
def fixture_default_branch() -> str:
    """Get the default branch name."""
    return "main"


@pytest.fixture(name="test_branch")
def fixture_test_branch() -> str:
    """Get the name of the branch to run tests on."""
    return "test"


@pytest.fixture(name="upstream_repository")
def fixture_upstream_repository(
    upstream_repository_path: Path, default_branch: str, test_branch: str
) -> Repo:
    """Initialize upstream repository."""
    upstream_repository = Repo.init(upstream_repository_path)
    writer = upstream_repository.config_writer()
    writer.set_value("user", "name", "upstream_user")
    writer.set_value("user", "email", "upstream_email")
    writer.release()
    upstream_repository.git.checkout("-b", default_branch)
    (upstream_repository_path / ".gitkeep").touch()
    upstream_repository.git.add(".")
    upstream_repository.git.commit("-m", "'initial commit'")
    upstream_repository.git.checkout("-b", test_branch)

    return upstream_repository


@pytest.fixture(name="repository_path")
def fixture_repository_path(tmp_path: Path) -> Path:
    """Create path for testing repository."""
    repo_path = tmp_path / "mocked"
    repo_path.mkdir()
    return repo_path


@pytest.fixture(name="repository")
def fixture_repository(
    upstream_repository: Repo,
    upstream_repository_path: Path,
    repository_path: Path,
    test_branch: str,
) -> Repo:
    """Create repository with mocked upstream."""
    # uptream_repository is added to create a dependency for the current fixture in order to ensure
    # that the repository can be cloned after the upstream has fully initialized.
    del upstream_repository

    repo = Repo.clone_from(url=upstream_repository_path, to_path=repository_path)
    repo.git.fetch()
    repo.git.checkout(test_branch)

    # Go into detached head mode to reflect how GitHub performs the checkout
    repo.head.set_reference(repo.head.commit.hexsha)
    repo.git.checkout(repo.head.commit.hexsha)

    return repo


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
def fixture_mock_github_repo(mock_pull_request: PullRequest, default_branch: str) -> Repository:
    """Create a mock github repository instance."""
    mocked_repo = mock.MagicMock(spec=Repository)
    mocked_repo.create_pull.return_value = mock_pull_request
    mocked_repo.full_name = "test/repository"
    mocked_repo.default_branch = default_branch
    return mocked_repo


@pytest.fixture(name="mock_github")
def fixture_mock_github(mock_github_repo: Repository) -> Github:
    """Create a mock github instance."""
    mocked_github = mock.MagicMock(spec=Github)
    mocked_github.get_repo.return_value = mock_github_repo
    return mocked_github


@pytest.fixture(name="repository_client")
def fixture_repository_client(
    repository: Repo, mock_github_repo: Repository
) -> pull_request.RepositoryClient:
    """Get repository client."""
    return pull_request.RepositoryClient(repository=repository, github_repository=mock_github_repo)


@pytest.fixture(name="patch_create_repository_client")
def fixture_patch_create_repository_client(
    monkeypatch: pytest.MonkeyPatch, repository_client: pull_request.RepositoryClient
) -> None:
    """Patch create_repository_client to return a mocked RepositoryClient."""

    def mock_create_repository_client(access_token: str | None, base_path: Path):
        """Mock create_repository_client patch function."""  # noqa: DCO020
        # to accept keywords as arguments
        del access_token
        del base_path

        return repository_client  # noqa: DCO030

    monkeypatch.setattr(src, "create_repository_client", mock_create_repository_client)
