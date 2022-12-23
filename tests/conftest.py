# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all tests."""

from pathlib import Path
from unittest import mock

import pytest
from git.repo import Repo
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.Requester import Requester


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
        attributes={"url": "test_url"},
        completed=False,
    )


@pytest.fixture(name="mock_github_repo")
def fixture_mock_github_repo(mock_pull_request: PullRequest):
    """Create a mock github repository instance."""
    mocked_repo = mock.MagicMock(spec=Repository)
    mocked_repo.create_pull.return_value = mock_pull_request
    return mocked_repo
