# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for git."""

# Need access to protected functions for testing
# pylint: disable=protected-access

import logging
import typing
from os.path import dirname
from pathlib import Path
from unittest import mock

import pytest
from git.exc import GitCommandError
from git.repo import Repo
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from src import pull_request
from src.exceptions import GitError, InputError

from .helpers import assert_substrings_in_string, create_repository_author


def test__configure_user(repository: tuple[Repo, Path]):
    """
    arrange: given a git repository without profile
    act: when _configure_user is called
    assert: default user and email are configured as profile.
    """
    (repo, _) = repository

    pull_request._configure_user(repo)

    reader = repo.config_reader()
    assert reader.get_value("user", "name") == pull_request.ACTIONS_USER_NAME
    assert reader.get_value("user", "email") == pull_request.ACTIONS_USER_EMAIL


def test__create_pull_request_dry_run(
    mock_github_repo: Repository,
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given a mocked github repository client and a mocked pull request
    act: when _create_pull_request is called with dry_run True,
    assert: a dry run pull request link is returned.
    """
    caplog.set_level(logging.INFO)
    assert (
        pull_request._create_pull_request(
            github_repository=mock_github_repo,
            branch_name="branch-1",
            base="base-1",
            dry_run=True,
        )
        == pull_request.PR_LINK_DRY_RUN
    )
    assert "create pull request" in caplog.text
    assert f"dry run: {True}" in caplog.text


def test__create_pull_request(mock_pull_request: PullRequest, mock_github_repo: Repository):
    """
    arrange: given a mocked github repository client and a mocked pull request
    act: when _create_pull_request is called with dry_run False,
    assert: a pull request link is returned.
    """
    assert (
        pull_request._create_pull_request(
            github_repository=mock_github_repo,
            branch_name="branch-1",
            base="base-1",
            dry_run=False,
        )
        == mock_pull_request.url
    )


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
    assert: GitError is raised.
    """
    with pytest.raises(GitError):
        pull_request.get_repository_name(remote_url=remote_url)


# Pylint doesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable,too-many-locals
@pytest.mark.parametrize(
    "remote_url, expected_repository_name",
    [
        pytest.param(
            "https://github.com/canonical/upload-charm-docs",
            valid_url := "canonical/upload-charm-docs",
            id="valid url",
        ),
        pytest.param(
            "https://github.com/canonical/upload-charm-docs.git",
            valid_url,
            id="valid git url",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test_get_repository_name(remote_url: str, expected_repository_name: str):
    """
    arrange: given a non-valid remote_url
    act: when _get_repository_name is called
    assert: GitError is raised.
    """
    assert pull_request.get_repository_name(remote_url=remote_url) == expected_repository_name


def test__check_branch_exists_error(tmp_path: Path):
    """
    arrange: given an invalid repository with no origin upstream
    act: when _check_branch_exists is called with a branch_name that doesn't exist
    assert: a GitCommandError is raised.
    """
    branch_name = "branch_name"
    repo = Repo.init(tmp_path)
    with pytest.raises(GitCommandError):
        pull_request._check_branch_exists(repo, branch_name)


def test__check_branch_exists_not_exist(repository: tuple[Repo, Path]):
    """
    arrange: given a git repository
    act: when _check_branch_exists is called with a branch_name that does not exist
    assert: False is returned.
    """
    (repo, _) = repository
    branch_name = "no-such-branchname"
    assert not pull_request._check_branch_exists(repo, branch_name)


def test__check_branch_exists(
    upstream_repository: tuple[Repo, Path], repository: tuple[Repo, Path]
):
    """
    arrange: given a local git repository and an upstream repository with a branch
    act: when _check_branch_exists is called with a branch_name that exists
    assert: True is returned.
    """
    branch_name = "branch_name"
    (upstream_repo, _) = upstream_repository
    upstream_repo.create_head(branch_name)
    (repo, _) = repository
    assert pull_request._check_branch_exists(repo, branch_name)


@pytest.mark.parametrize(
    "existing_files, new_files",
    [
        pytest.param(
            [original_file := (Path("text.txt"), "original")],
            [test_file := (Path("test.txt"), "test")],
            id="simple merge",
        ),
    ],
)
def test__merge_existing_branch_dry_run(
    existing_files: list[tuple[Path, str]],
    new_files: list[tuple[Path, str]],
    upstream_repository: tuple[Repo, Path],
    repository: tuple[Repo, Path],
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given a local git repository with changes and \
        a remote repository with existing branch with existing files
    act: when _merge_existing_branch is called with existing branch name \
        in dry run mode
    assert: then no changes are merged, and the action is logged.
    """
    caplog.set_level(logging.INFO)
    branch_name = "test_branch"
    commit_message = "test_message"
    (upstream, upstream_path) = upstream_repository
    upstream_head = upstream.create_head(branch_name)
    upstream_head.checkout()
    for (file, content) in existing_files:
        (upstream_path / file).touch()
        (upstream_path / file).write_text(content, encoding="utf-8")
    upstream.git.add(".")
    upstream.git.commit("-m", "'add upstream'")
    upstream.git.checkout("main")
    (repo, repo_path) = repository
    for (file, content) in new_files:
        (repo_path / file).touch()
        (repo_path / file).write_text(content, encoding="utf-8")
    repo.git.fetch("origin", branch_name)
    create_repository_author(repo)

    pull_request._merge_existing_branch(
        repository=repo, branch_name=branch_name, commit_msg=commit_message, dry_run=True
    )

    upstream.git.checkout(branch_name)
    assert f"dry run: {True}" in caplog.text
    assert "merge to existing branch" in caplog.text
    for (file, content) in new_files:
        assert not (upstream_path / file).is_file()


@pytest.mark.parametrize(
    "existing_files, new_files, expected_files",
    [
        pytest.param(
            [original_file := (Path("text.txt"), "original")],
            [test_file := (Path("test.txt"), "test")],
            [
                original_file,
                test_file,
            ],
            id="simple merge",
        ),
        pytest.param(
            [original_file],
            [updated_file := (Path("text.txt"), "update")],
            [updated_file],
            id="merge incoming",
        ),
    ],
)
def test__merge_existing_branch(
    existing_files: list[tuple[Path, str]],
    new_files: list[tuple[Path, str]],
    expected_files: list[tuple[Path, str]],
    upstream_repository: tuple[Repo, Path],
    repository: tuple[Repo, Path],
):
    """
    arrange: given a local git repository with changes and \
        a remote repository with existing branch with existing files
    act: when _merge_existing_branch is called with existing branch name
    assert: files are merged with expected content upstream.
    """
    branch_name = "test_branch"
    commit_message = "test_message"
    (upstream, upstream_path) = upstream_repository
    upstream_head = upstream.create_head(branch_name)
    upstream_head.checkout()
    for (file, content) in existing_files:
        (upstream_path / file).touch()
        (upstream_path / file).write_text(content, encoding="utf-8")
    upstream.git.add(".")
    upstream.git.commit("-m", "'add upstream'")
    upstream.git.checkout("main")
    (repo, repo_path) = repository
    for (file, content) in new_files:
        (repo_path / file).touch()
        (repo_path / file).write_text(content, encoding="utf-8")
    repo.git.fetch("origin", branch_name)
    create_repository_author(repo)

    pull_request._merge_existing_branch(
        repository=repo, branch_name=branch_name, commit_msg=commit_message, dry_run=False
    )

    upstream.git.checkout(branch_name)
    for (file, content) in expected_files:
        assert (upstream_path / file).is_file()
        assert (upstream_path / file).read_text(encoding="utf-8") == content


@pytest.mark.parametrize(
    "new_files",
    [
        pytest.param([test_file], id="single file"),
        pytest.param(
            [test_file, nested_file := (Path("nested/file.txt"), "nested file content")],
            id="nested file",
        ),
    ],
)
def test__create_branch_dry_run(
    new_files: list[tuple[Path, str]],
    upstream_repository: tuple[Repo, Path],
    repository: tuple[Repo, Path],
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given a local git repository with new files
    act: when _create_branch is called with new branch name in dry run mode
    assert: new files are created upstream.
    """
    caplog.set_level(logging.INFO)
    branch_name = "test_branch"
    (upstream, upstream_path) = upstream_repository
    (repo, repo_path) = repository
    for (file, content) in new_files:
        Path(dirname(repo_path / file)).mkdir(parents=True, exist_ok=True)
        (repo_path / file).touch()
        (repo_path / file).write_text(content, encoding="utf-8")
    create_repository_author(repo)

    pull_request._create_branch(
        repository=repo, branch_name=branch_name, commit_msg="test_commit", dry_run=True
    )

    assert f"dry run: {True}" in caplog.text
    assert "create new branch" in caplog.text
    with pytest.raises(GitCommandError) as exc_info:
        upstream.git.checkout(branch_name)
    assert_substrings_in_string(
        ("error: pathspec", "did not match any file(s) known to git"), str(exc_info.value)
    )


@pytest.mark.parametrize(
    "new_files",
    [
        pytest.param([test_file], id="single file"),
        pytest.param(
            [test_file, nested_file := (Path("nested/file.txt"), "nested file content")],
            id="nested file",
        ),
    ],
)
def test__create_branch(
    new_files: list[tuple[Path, str]],
    upstream_repository: tuple[Repo, Path],
    repository: tuple[Repo, Path],
):
    """
    arrange: given a local git repository with new files
    act: when _create_branch is called with new branch name
    assert: new files are created upstream.
    """
    branch_name = "test_branch"
    (upstream, upstream_path) = upstream_repository
    (repo, repo_path) = repository
    for (file, content) in new_files:
        Path(dirname(repo_path / file)).mkdir(parents=True, exist_ok=True)
        (repo_path / file).touch()
        (repo_path / file).write_text(content, encoding="utf-8")
    create_repository_author(repo)

    pull_request._create_branch(
        repository=repo, branch_name=branch_name, commit_msg="test_commit", dry_run=False
    )

    upstream.git.checkout(branch_name)
    for (file, content) in new_files:
        assert (upstream_path / file).is_file()


@pytest.mark.parametrize(
    "access_token, expected_error_msg_contents",
    [
        pytest.param(
            "",
            (err_strs := ("invalid", "access_token", "input", "must be non-empty")),
            id="No access token",
        ),
        pytest.param(
            {},
            err_strs,
            id="Invalid access token type(empty)",
        ),
        pytest.param(
            1234,
            ("invalid", "access_token", "input", "must be a string"),
            id="invalid access token type(numeric)",
        ),
    ],
)
def test_create_github_instance_error(
    access_token: typing.Any, expected_error_msg_contents: tuple[str, ...]
):
    """
    arrange: Given an invalid access token input
    act: when create_github_repository_instance is called
    assert: InputError is raised with invalid access token info.
    """
    with pytest.raises(InputError) as exc_info:
        pull_request.create_github(access_token=access_token)

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())


def test_create_github_instance():
    """
    arrange: Given a valid access token
    act: when create_github_repository_instance is called
    assert: valid Github instance is returned.
    """
    # bandit will not let hardcoded passwords pass
    access_token = "valid-access-token"  # nosec
    assert isinstance(pull_request.create_github(access_token=access_token), Github)


def test_create_pull_request_invalid_branch(tmp_path: Path, mock_github_repo: Repository):
    """
    arrange: given a repository and a mocked github repository and a branch_name that is equal
        to the base branch
    act: when create_pull_request is called
    assert: InputError is raised with error message.
    """
    branch_name = "test-branch"
    # Setting up an exiting branch requires a head in an empty repository.
    # Committing an empty file allows so.
    repo = Repo.init(tmp_path)
    create_repository_author(repo)
    (tmp_path / "test.txt").touch()
    repo.git.add(".")
    repo.git.commit("-m", "test commit")
    current_branch = repo.create_head(branch_name)
    current_branch.checkout()

    with pytest.raises(InputError) as exc_info:
        pull_request.create_pull_request(
            repository=repo,
            github_repository=mock_github_repo,
            branch_name=branch_name,
            dry_run=False,
        )

    assert_substrings_in_string(
        ("branch name", "cannot be equal", "base branch"), str(exc_info.value).lower()
    )


def test_create_pull_request_no_change(
    repository: tuple[Repo, Path], mock_github_repo: Repository
):
    """
    arrange: given a repository and a mocked github repository with no changed file
    act: when create_pull_request is called
    assert: Nothing is returned.
    """
    branch_name = "test_branch_name"
    (repo, _) = repository

    returned_pr = pull_request.create_pull_request(
        repository=repo, github_repository=mock_github_repo, branch_name=branch_name, dry_run=False
    )

    assert returned_pr == pull_request.PR_LINK_NO_CHANGE


def test_create_pull_request_existing_branch(
    repository: tuple[Repo, Path],
    upstream_repository: tuple[Repo, Path],
    mock_github_repo: Repository,
):
    """
    arrange: given a mocked repository with a new file and a mocked github repository \
        with an existing branch and no existing pull request
    act: when create_pull_request is called
    assert: a github PR link is returned.
    """
    branch_name = "test_branch_name"
    (repo, repo_path) = repository
    test_file = "file.md"
    (repo_path / test_file).touch()
    (upstream, upstream_path) = upstream_repository
    upstream.create_head(branch_name)
    mock_github_repo = mock.MagicMock(spec=Repository)

    pr_link = pull_request.create_pull_request(
        repository=repo, github_repository=mock_github_repo, branch_name=branch_name, dry_run=False
    )

    upstream.git.checkout(branch_name)
    (upstream_path / test_file).is_file()
    assert pr_link is not None
    mock_github_repo.get_pulls.assert_called_once_with(
        state="open",
        head=f"{pull_request.ACTIONS_USER_NAME}/{branch_name}",
    )
    mock_github_repo.create_pull.assert_called_once_with(
        title=pull_request.ACTIONS_PULL_REQUEST_TITLE,
        body=pull_request.ACTIONS_PULL_REQUEST_BODY,
        base="main",
        head=branch_name,
    )


def test_create_pull_request(
    repository: tuple[Repo, Path],
    upstream_repository: tuple[Repo, Path],
    mock_github_repo: mock.MagicMock,
):
    """
    arrange: given a mocked repository with a new file and a mocked github repository \
        and no existing pull request
    act: when create_pull_request is called
    assert: a github PR link is returned.
    """
    branch_name = "test_branch_name"
    (repo, repo_path) = repository
    test_file = "file.md"
    (repo_path / test_file).touch()

    pr_link = pull_request.create_pull_request(
        repository=repo, github_repository=mock_github_repo, branch_name=branch_name, dry_run=False
    )

    (upstream, upstream_path) = upstream_repository
    upstream.git.checkout(branch_name)
    (upstream_path / test_file).is_file()
    assert pr_link is not None
    mock_github_repo.get_pulls.assert_called_once_with(
        state="open",
        head=f"{pull_request.ACTIONS_USER_NAME}/{branch_name}",
    )
    mock_github_repo.create_pull.assert_called_once_with(
        title=pull_request.ACTIONS_PULL_REQUEST_TITLE,
        body=pull_request.ACTIONS_PULL_REQUEST_BODY,
        base="main",
        head=branch_name,
    )


def test_create_pull_request_existing_pr(
    repository: tuple[Repo, Path],
    upstream_repository: tuple[Repo, Path],
    mock_github_repo: mock.MagicMock,
    mock_pull_request: PullRequest,
):
    """
    arrange: given a mocked repository with a new file and a mocked github repository \
        and no existing pull request
    act: when create_pull_request is called
    assert: a github PR link is returned.
    """
    branch_name = "test_branch_name"
    (repo, repo_path) = repository
    create_repository_author(repo)
    test_file = "file.md"
    (repo_path / test_file).touch()
    mock_github_repo.get_pulls.side_effect = [[mock_pull_request]]

    pr_link = pull_request.create_pull_request(
        repository=repo, github_repository=mock_github_repo, branch_name=branch_name, dry_run=False
    )

    (upstream, upstream_path) = upstream_repository
    upstream.git.checkout(branch_name)
    (upstream_path / test_file).is_file()
    assert pr_link == mock_pull_request.url
    mock_github_repo.get_pulls.assert_called_once_with(
        state="open",
        head=f"{pull_request.ACTIONS_USER_NAME}/{branch_name}",
    )
