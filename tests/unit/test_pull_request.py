# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for git."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from unittest import mock

import pytest
from git.exc import GitCommandError
from git.repo import Repo
from github.GithubException import GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

from src import pull_request
from src.exceptions import InputError, RepositoryClientError
from src.pull_request import RepositoryClient

from .helpers import assert_substrings_in_string


def test___init__(repository: tuple[Repo, Path], mock_github_repo: Repository):
    """
    arrange: given a local git repository client and mock github repository client
    act: when RepositoryClient is initialized
    assert: RepositoryClient is created and git user is configured.
    """
    (repo, _) = repository

    repository_client = pull_request.RepositoryClient(
        repository=repo, github_repository=mock_github_repo
    )

    config_reader = repository_client._git_repo.config_reader()
    assert config_reader.get_value("user", "name") == pull_request.ACTIONS_USER_NAME
    assert config_reader.get_value("user", "email") == pull_request.ACTIONS_USER_EMAIL


def test__check_branch_exists_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: RepositoryClient
):
    """
    arrange: given RepositoryClient with a mocked local git repository client that raises an
        exception
    act: when _check_branch_exists is called
    assert: RepositoryClientError is raised from GitCommandError.
    """
    err_str = "mocked error"
    mock_git_repository = mock.MagicMock(spec=Repo)
    mock_git_repository.git.fetch.side_effect = [GitCommandError(err_str)]
    monkeypatch.setattr(repository_client, "_git_repo", mock_git_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client._check_branch_exists("branchname-1")

    assert_substrings_in_string(
        ("unexpected error checking existing branch", err_str), str(exc.value).lower()
    )


def test__check_branch_not_exists(repository_client: RepositoryClient):
    """
    arrange: given RepositoryClient with an upstream repository
    act: when _check_branch_exists is called
    assert: False is returned.
    """
    assert not repository_client._check_branch_exists("no-such-branchname")


def test__check_branch_exists(
    repository_client: RepositoryClient, upstream_repository: tuple[Repo, Path]
):
    """
    arrange: given RepositoryClient with an upstream repository with check-branch-exists branch
    act: when _check_branch_exists is called
    assert: True is returned.
    """
    (upstream_repo, upstream_path) = upstream_repository
    branch_name = "check-branch-exists"
    head = upstream_repo.create_head(branch_name)
    head.checkout()
    (upstream_path / "filler-file").touch()
    upstream_repo.git.add(".")
    upstream_repo.git.commit("-m", "test")

    assert repository_client._check_branch_exists(branch_name)

    upstream_repo.git.checkout("main")
    upstream_repo.git.branch("-D", branch_name)


def test__create_branch_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: RepositoryClient
):
    """
    arrange: given RepositoryClient with a mocked local git repository that raises an exception
    act: when _create_branch is called
    assert: RepositoryClientError is raised.
    """
    err_str = "mocked error"
    mock_git_repository = mock.MagicMock(spec=Repo)
    mock_git_repository.git.fetch.side_effect = [GitCommandError(err_str)]
    monkeypatch.setattr(repository_client, "_git_repo", mock_git_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client._create_branch(branch_name="test-create-branch", commit_msg="commit-1")

    assert_substrings_in_string(
        ("unexpected error checking existing branch", err_str), str(exc.value).lower()
    )


def test__create_branch(
    repository_client: RepositoryClient, upstream_repository: tuple[Repo, Path]
):
    """
    arrange: given RepositoryClient
    act: when _create_branch is called
    assert: a new branch is successfully created upstream.
    """
    (upstream_repo, _) = upstream_repository
    branch_name = "test-create-branch"

    repository_client._create_branch(branch_name=branch_name, commit_msg="commit-1")

    assert any(branch for branch in upstream_repo.branches if branch.name == branch_name)


def test__create_github_pull_request_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: RepositoryClient
):
    """
    arrange: given RepositoryClient with a mocked github repository client that raises an exception
    act: when _create_github_pull_request is called
    assert: RepositoryClientError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.create_pull.fetch.side_effect = [GithubException]
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client._create_github_pull_request(
            branch_name="branchname-1", base="base-branchname"
        )

    assert_substrings_in_string(
        ("unexpected error creating pull request", "githubexception"), str(exc.value).lower()
    )


def test__create_github_pull_request(
    repository_client: RepositoryClient, mock_pull_request: PullRequest
):
    """
    arrange: given RepositoryClient with a mocked github client that returns a mocked pull request
    act: when _create_github_pull_request is called
    assert: a pull request's page link is returned.
    """
    returned_url = repository_client._create_github_pull_request("branchname-1", "base-branchname")

    assert returned_url == mock_pull_request.html_url


def test_create_pull_request_on_default_branchname(
    monkeypatch: pytest.MonkeyPatch,
    repository_client: RepositoryClient,
):
    """
    arrange: given RepositoryClient with a mocked local git client that is on default branchname
    act: when create_pull_request is called
    assert: InputError is raised.
    """
    mock_git_repository = mock.MagicMock(spec=Repo)
    mock_git_repository.active_branch_name = pull_request.DEFAULT_BRANCH_NAME
    monkeypatch.setattr(repository_client, "_git_repo", mock_git_repository)

    with pytest.raises(InputError):
        repository_client.create_pull_request()


def test_create_pull_request_no_dirty_files(
    repository_client: RepositoryClient,
):
    """
    arrange: given RepositoryClient with no dirty files
    act: when create_pull_request is called
    assert: InputError is raised.
    """
    with pytest.raises(InputError):
        repository_client.create_pull_request()


def test_create_pull_request_existing_branch(
    repository_client: RepositoryClient, upstream_repository: tuple[Repo, Path]
):
    """
    arrange: given RepositoryClient and an upstream repository that already has migration branch
    act: when create_pull_request is called
    assert: InputError is raised.
    """
    (upstream_repo, upstream_path) = upstream_repository
    branch_name = pull_request.DEFAULT_BRANCH_NAME
    head = upstream_repo.create_head(branch_name)
    head.checkout()
    (upstream_path / "filler-file").touch()
    upstream_repo.git.add(".")
    upstream_repo.git.commit("-m", "test")

    with pytest.raises(InputError):
        repository_client.create_pull_request()

    upstream_repo.git.checkout("main")
    upstream_repo.git.branch("-D", branch_name)


def test_create_pull_request(
    repository_client: RepositoryClient,
    upstream_repository: tuple[Repo, Path],
    repository: tuple[Repo, Path],
    mock_pull_request: PullRequest,
):
    """
    arrange: given RepositoryClient and a repository with changed files
    act: when create_pull_request is called
    assert: changes are pushed to default branch and pull request link is returned.
    """
    (_, repo_path) = repository
    filler_filename = "filler-file"
    filler_file = repo_path / filler_filename
    filler_text = "filler-text"
    filler_file.write_text(filler_text)

    returned_pr_link = repository_client.create_pull_request()

    (upstream_repo, upstream_path) = upstream_repository
    upstream_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert returned_pr_link == mock_pull_request.html_url
    assert (upstream_path / filler_filename).read_text() == filler_text


@pytest.mark.parametrize(
    "remote_url",
    [
        pytest.param("https://gitlab.com/canonical/upload-charm-docs.git", id="non-github url"),
        pytest.param("http://gitlab.com/canonical/upload-charm-docs.git", id="http url"),
        pytest.param("git@github.com:yanksyoon/actionrefer.git", id="ssh url"),
    ],
)
def test_get_repository_name_invalid(remote_url: str):
    """
    arrange: given a non-valid remote_url
    act: when _get_repository_name is called
    assert: InputError is raised.
    """
    with pytest.raises(InputError):
        pull_request._get_repository_name_from_git_url(remote_url=remote_url)


@pytest.mark.parametrize(
    "remote_url, expected_repository_name",
    [
        pytest.param(
            "https://github.com/canonical/upload-charm-docs",
            "canonical/upload-charm-docs",
            id="valid url",
        ),
        pytest.param(
            "https://github.com/canonical/upload-charm-docs.git",
            "canonical/upload-charm-docs",
            id="valid git url",
        ),
    ],
)
def test_get_repository_name(remote_url: str, expected_repository_name: str):
    """
    arrange: given a non-valid remote_url
    act: when _get_repository_name is called
    assert: GitError is raised.
    """
    assert (
        pull_request._get_repository_name_from_git_url(remote_url=remote_url)
        == expected_repository_name
    )


def test_create_repository_client_no_token(repository: tuple[Repo, Path]):
    """
    arrange: given valid repository path and empty access_token
    act: when create_repository_client_no_token is called
    assert: InputError is raised.
    """
    (_, repo_path) = repository
    test_token = ""

    with pytest.raises(InputError):
        pull_request.create_repository_client(access_token=test_token, base_path=repo_path)
