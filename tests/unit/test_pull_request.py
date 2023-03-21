# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for git."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path

import pytest
from git.repo import Repo
from github.PullRequest import PullRequest

from src import pull_request
from src.exceptions import InputError
from src.index import DOCUMENTATION_FOLDER_NAME
from src.pull_request import RepositoryClient

from .helpers import assert_substrings_in_string


def test_create_pull_request_no_dirty_files(repository_client: RepositoryClient):
    """
    arrange: given RepositoryClient with no dirty files
    act: when create_pull_request is called
    assert: InputError is raised.
    """
    with pytest.raises(InputError) as exc:
        pull_request.create_pull_request(repository=repository_client)

    assert_substrings_in_string(
        ("no files seem to be migrated. please add contents upstream first.",),
        str(exc.value).lower(),
    )


def test_create_pull_request_existing_branch(
    repository_client: RepositoryClient,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    repository_path: Path,
):
    """
    arrange: given RepositoryClient and an upstream repository that already has migration branch
    act: when create_pull_request is called
    assert: InputError is raised.
    """
    docs_folder = Path(DOCUMENTATION_FOLDER_NAME)
    (repository_path / docs_folder).mkdir()
    filler_file = docs_folder / "filler-file"
    (repository_path / filler_file).write_text("filler-content")

    branch_name = pull_request.DEFAULT_BRANCH_NAME
    head = upstream_git_repo.create_head(branch_name)
    head.checkout()
    (upstream_repository_path / docs_folder).mkdir()
    (upstream_repository_path / filler_file).touch()
    upstream_git_repo.git.add(".")
    upstream_git_repo.git.commit("-m", "test")

    with pytest.raises(InputError) as exc:
        pull_request.create_pull_request(repository=repository_client)

    assert_substrings_in_string(
        (
            "branch",
            "already exists",
            "please try again after removing",
            pull_request.DEFAULT_BRANCH_NAME,
        ),
        str(exc.value).lower(),
    )


def test_create_pull_request(
    repository_client: RepositoryClient,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    repository_path: Path,
    mock_pull_request: PullRequest,
):
    """
    arrange: given RepositoryClient and a repository with changed files
    act: when create_pull_request is called
    assert: changes are pushed to default branch and pull request link is returned.
    """
    docs_folder = Path(DOCUMENTATION_FOLDER_NAME)
    (repository_path / docs_folder).mkdir()
    filler_file = docs_folder / "filler.txt"
    filler_text = "filler-text"
    (repository_path / filler_file).write_text(filler_text)

    returned_pr_link = pull_request.create_pull_request(repository=repository_client)

    upstream_git_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert returned_pr_link == mock_pull_request.html_url
    assert (upstream_repository_path / filler_file).read_text() == filler_text
