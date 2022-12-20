# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for all tests."""

from pathlib import Path

import pytest
from git.repo import Repo


@pytest.fixture(name="upstream_repository")
def fixture_upstream_repository(tmp_path: Path) -> tuple[Repo, Path]:
    """Create upstream repository."""
    upstream_path = tmp_path / "upstream"
    upstream_path.mkdir()
    upstream = Repo.init(upstream_path)
    upstream.git.checkout("-b", "main")
    (upstream_path / ".gitkeep").touch()
    upstream.git.add(".")
    upstream.git.commit("-m", "'initial commit'")

    return (upstream, upstream_path)


@pytest.fixture(name="repository")
def repository(upstream_repository: tuple[Repo, Path], tmp_path: Path) -> tuple[Repo, Path]:
    """Create repository with mocked upstream."""
    (_, upstream_path) = upstream_repository
    repo_path = tmp_path / "mocked"
    repo_path.mkdir()
    repo = Repo.clone_from(url=upstream_path, to_path=repo_path)
    return (repo, repo_path)
