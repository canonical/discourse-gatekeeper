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
from github import Github
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
        repository_client.check_branch_exists("branchname-1")

    assert_substrings_in_string(
        ("unexpected error checking existing branch", err_str), str(exc.value).lower()
    )


def test__check_branch_not_exists(repository_client: RepositoryClient):
    """
    arrange: given RepositoryClient with an upstream repository
    act: when _check_branch_exists is called
    assert: False is returned.
    """
    assert not repository_client.check_branch_exists("no-such-branchname")


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

    assert repository_client.check_branch_exists(branch_name)


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
    mock_git_repository.git.commit.side_effect = [GitCommandError(err_str)]
    monkeypatch.setattr(repository_client, "_git_repo", mock_git_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.create_branch(branch_name="test-create-branch", commit_msg="commit-1")

    assert_substrings_in_string(
        ("unexpected error creating new branch", err_str), str(exc.value).lower()
    )


def test__create_branch(
    repository_client: RepositoryClient,
    repository: tuple[Repo, Path],
    upstream_repository: tuple[Repo, Path],
):
    """
    arrange: given RepositoryClient and newly created files in repo directory
    act: when _create_branch is called
    assert: a new branch is successfully created upstream.
    """
    (_, repo_path) = repository
    testfile = "testfile.txt"
    testfile_content = "test"
    (repo_path / testfile).write_text(testfile_content)
    (upstream_repo, _) = upstream_repository
    branch_name = "test-create-branch"

    repository_client.create_branch(branch_name=branch_name, commit_msg="commit-1")

    # mypy false positive in lib due to getter/setter not being next to each other.
    assert any(
        branch for branch in upstream_repo.branches if branch.name == branch_name  # type: ignore
    )


def test__create_pull_request_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: RepositoryClient
):
    """
    arrange: given RepositoryClient with a mocked github repository client that raises an exception
    act: when _create_pull_request is called
    assert: RepositoryClientError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.create_pull.side_effect = [
        GithubException(status=500, data="Internal Server Error", headers=None)
    ]
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.create_pull_request(branch_name="branchname-1", base="base-branchname")

    assert_substrings_in_string(
        ("unexpected error creating pull request", "githubexception"), str(exc.value).lower()
    )


def test__create_pull_request(repository_client: RepositoryClient, mock_pull_request: PullRequest):
    """
    arrange: given RepositoryClient with a mocked github client that returns a mocked pull request
    act: when _create_pull_request is called
    assert: a pull request's page link is returned.
    """
    returned_url = repository_client.create_pull_request("branchname-1", "base-branchname")

    assert returned_url == mock_pull_request.html_url


def test_create_pull_request_on_default_branchname(
    repository: tuple[Repo, Path],
    repository_client: RepositoryClient,
):
    """
    arrange: given RepositoryClient with a mocked local git client that is on default branchname
    act: when create_pull_request is called
    assert: InputError is raised.
    """
    (repo, _) = repository
    head = repo.create_head(pull_request.DEFAULT_BRANCH_NAME)
    head.checkout()

    with pytest.raises(InputError) as exc:
        pull_request.create_pull_request(repository=repository_client)

    assert_substrings_in_string(
        (
            "pull request branch cannot be named",
            "please try again after changing the branch name.",
            pull_request.DEFAULT_BRANCH_NAME,
        ),
        str(exc.value).lower(),
    )


def test_create_pull_request_no_dirty_files(
    repository_client: RepositoryClient,
):
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
    upstream_repository: tuple[Repo, Path],
    repository: tuple[Repo, Path],
):
    """
    arrange: given RepositoryClient and an upstream repository that already has migration branch
    act: when create_pull_request is called
    assert: InputError is raised.
    """
    (_, repo_path) = repository
    (repo_path / "filler-file").write_text("filler-content")
    (upstream_repo, upstream_path) = upstream_repository
    branch_name = pull_request.DEFAULT_BRANCH_NAME
    head = upstream_repo.create_head(branch_name)
    head.checkout()
    (upstream_path / "filler-file").touch()
    upstream_repo.git.add(".")
    upstream_repo.git.commit("-m", "test")

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

    returned_pr_link = pull_request.create_pull_request(repository=repository_client)

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
    with pytest.raises(InputError) as exc:
        pull_request._get_repository_name_from_git_url(remote_url=remote_url)

    assert_substrings_in_string(
        ("invalid remote repository url",),
        str(exc.value).lower(),
    )


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
    act: when create_repository_client is called
    assert: InputError is raised.
    """
    (_, repo_path) = repository
    # the following token is for testing purposes only.
    test_token = ""  # nosec

    with pytest.raises(InputError) as exc:
        pull_request.create_repository_client(access_token=test_token, base_path=repo_path)

    assert_substrings_in_string(
        ("invalid", "access_token", "input", "it must be", "non-empty"),
        str(exc.value).lower(),
    )


def test_create_repository_client(
    monkeypatch: pytest.MonkeyPatch, repository: tuple[Repo, Path], mock_github_repo: Repository
):
    """
    arrange: given valid repository path and a valid access_token and a mocked github client
    act: when create_repository_client is called
    assert: RepositoryClient is returned.
    """
    (repo, repo_path) = repository
    origin = repo.remote("origin")
    repo.delete_remote(origin)
    repo.create_remote("origin", "https://github.com/test-user/test-repo.git")
    # the following token is for testing purposes only.
    test_token = "testing-token"  # nosec
    mock_github_client = mock.MagicMock(spec=Github)
    mock_github_client.get_repo.returns = mock_github_repo
    monkeypatch.setattr(pull_request, "Github", mock_github_client)

    returned_client = pull_request.create_repository_client(
        access_token=test_token, base_path=repo_path
    )

    assert isinstance(returned_client, pull_request.RepositoryClient)
