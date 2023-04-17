# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for git."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path

import pytest
from git.repo import Repo
from github.PullRequest import PullRequest

from src import pull_request, repository
from src.constants import DEFAULT_BRANCH, DOCUMENTATION_FOLDER_NAME
from src.exceptions import InputError
from src.pull_request import RepositoryClient

from .helpers import assert_substrings_in_string


def test_create_pull_request_no_dirty_files(repository_client: RepositoryClient):
    """
    arrange: given RepositoryClient with no dirty files
    act: when create_pull_request is called
    assert: InputError is raised.
    """
    with pytest.raises(InputError) as exc:
        pull_request.create_pull_request(
            repository=repository_client.switch(DEFAULT_BRANCH), base=DEFAULT_BRANCH
        )

    assert_substrings_in_string(
        ("no files seem to be migrated. please add contents upstream first.",),
        str(exc.value).lower(),
    )


def test_create_pull_request_existing_branch(
    tmp_path: Path,
    repository_client: RepositoryClient,
    upstream_git_repo: Repo,
):
    """
    arrange: given RepositoryClient and an upstream repository that already has migration branch
    act: when create_pull_request is called
    assert: The remove branch is overridden
    """
    branch_name = pull_request.DEFAULT_BRANCH_NAME

    docs_folder = Path(DOCUMENTATION_FOLDER_NAME)
    filler_file = docs_folder / "filler-file"

    # Update docs branch from third repository
    third_repo_path = tmp_path / "third"
    third_repo = upstream_git_repo.clone(third_repo_path)

    writer = third_repo.config_writer()
    writer.set_value("user", "name", repository.ACTIONS_USER_NAME)
    writer.set_value("user", "email", repository.ACTIONS_USER_EMAIL)
    writer.release()

    third_repo.git.checkout("-b", branch_name)

    (third_repo_path / docs_folder).mkdir()
    (third_repo_path / filler_file).touch()
    third_repo.git.add(".")
    third_repo.git.commit("-m", "test")

    hash1 = third_repo.head.commit

    third_repo.git.push("--set-upstream", "origin", branch_name)

    repository_client.check_branch_exists(branch_name)
    repository_client.switch(branch_name).pull()

    hash2 = repository_client._git_repo.head.commit

    # make sure the hash of the upload-charm-docs/migrate branch agree
    assert hash1 == hash2

    repository_path = repository_client.switch(DEFAULT_BRANCH).base_path

    (repository_path / docs_folder).mkdir()
    (repository_path / filler_file).write_text("filler-content")

    pr_link = pull_request.create_pull_request(repository=repository_client, base=DEFAULT_BRANCH)

    repository_client.switch(branch_name).pull()

    hash3 = repository_client._git_repo.head.commit

    # Make sure that the upload-charm-docs/migrate branch has now be overridden
    assert hash2 != hash3
    assert pr_link == "test_url"


def test_create_pull_request(
    repository_client: RepositoryClient,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    mock_pull_request: PullRequest,
):
    """
    arrange: given RepositoryClient and a repository with changed files
    act: when create_pull_request is called
    assert: changes are pushed to default branch and pull request link is returned.
    """
    repository_path = repository_client.base_path

    docs_folder = Path(DOCUMENTATION_FOLDER_NAME)
    (repository_path / docs_folder).mkdir()
    filler_file = docs_folder / "filler.txt"
    filler_text = "filler-text"
    (repository_path / filler_file).write_text(filler_text)

    repository_client.switch(DEFAULT_BRANCH)

    returned_pr_link = pull_request.create_pull_request(
        repository=repository_client, base=DEFAULT_BRANCH
    )

    upstream_git_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert returned_pr_link == mock_pull_request.html_url
    assert (upstream_repository_path / filler_file).read_text() == filler_text
