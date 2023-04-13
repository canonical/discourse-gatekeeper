# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for git."""

# Need access to protected functions for testing
# pylint: disable=protected-access

import base64
import secrets
from pathlib import Path
from unittest import mock

import pytest
from git.exc import GitCommandError
from git.repo import Repo
from github import Github
from github.ContentFile import ContentFile
from github.GithubException import GithubException, UnknownObjectException
from github.PullRequest import PullRequest
from github.Repository import Repository

from src import repository
from src.constants import DOCUMENTATION_FOLDER_NAME
from src.exceptions import (
    InputError,
    RepositoryClientError,
    RepositoryFileNotFoundError,
    RepositoryTagNotFoundError,
)
from src.repository import Client

from .helpers import assert_substrings_in_string


def test__init__(git_repo: Repo, mock_github_repo: Repository):
    """
    arrange: given a local git repository client and mock github repository client
    act: when Client is initialized
    assert: Client is created and git user is configured.
    """
    repository.Client(repository=git_repo, github_repository=mock_github_repo)

    config_reader = git_repo.config_reader()
    assert config_reader.get_value(*repository.CONFIG_USER_NAME) == repository.ACTIONS_USER_NAME
    assert config_reader.get_value(*repository.CONFIG_USER_EMAIL) == repository.ACTIONS_USER_EMAIL


def test__init__name_email_set(git_repo: Repo, mock_github_repo: Repository):
    """
    arrange: given a local git repository client with the user and email configuration already set
        and mock github repository client
    act: when Client is initialized
    assert: Client is created and git user configuration is not overridden.
    """
    user_name = "name 1"
    user_email = "email 1"
    with git_repo.config_writer(config_level="repository") as config_writer:
        config_writer.set_value(*repository.CONFIG_USER_NAME, user_name)
        config_writer.set_value(*repository.CONFIG_USER_EMAIL, user_email)

    repository_client = repository.Client(repository=git_repo, github_repository=mock_github_repo)

    config_reader = repository_client._git_repo.config_reader()
    assert config_reader.get_value(*repository.CONFIG_USER_NAME) == user_name
    assert config_reader.get_value(*repository.CONFIG_USER_EMAIL) == user_email


def test_check_branch_exists_error(monkeypatch: pytest.MonkeyPatch, repository_client: Client):
    """
    arrange: given Client with a mocked local git repository client that raises an
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


def test_check_branch_not_exists(repository_client: Client):
    """
    arrange: given Client with an upstream repository
    act: when _check_branch_exists is called
    assert: False is returned.
    """
    assert not repository_client.check_branch_exists("no-such-branchname")


def test_check_branch_exists(
    repository_client: Client, upstream_git_repo: Repo, upstream_repository_path: Path
):
    """
    arrange: given Client with an upstream repository with check-branch-exists branch
    act: when _check_branch_exists is called
    assert: True is returned.
    """
    branch_name = "check-branch-exists"
    head = upstream_git_repo.create_head(branch_name)
    head.checkout()
    (upstream_repository_path / "filler-file").touch()
    upstream_git_repo.git.add(".")
    upstream_git_repo.git.commit("-m", "test")

    assert repository_client.check_branch_exists(branch_name)


def test_create_branch_error(monkeypatch: pytest.MonkeyPatch, repository_client: Client):
    """
    arrange: given Client with a mocked local git repository that raises an exception
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


def test_create_branch(
    repository_client: Client,
    repository_path: Path,
    upstream_git_repo: Repo,
):
    """
    arrange: given Client and newly created files in `repo` and `repo/docs` directories
    act: when _create_branch is called
    assert: a new branch is successfully created upstream with only the files in the `repo/docs`
        directory.
    """
    root_file = repository_path / "test.txt"
    root_file.write_text("content 1", encoding="utf-8")
    docs_dir = Path(DOCUMENTATION_FOLDER_NAME)
    (repository_path / docs_dir).mkdir()
    docs_file = docs_dir / "test.txt"
    (repository_path / docs_file).write_text("content 2", encoding="utf-8")
    nested_docs_dir = docs_dir / "nested"
    (repository_path / nested_docs_dir).mkdir()
    nested_docs_file = nested_docs_dir / "test.txt"
    (repository_path / nested_docs_file).write_text("content 3", encoding="utf-8")
    branch_name = "test-create-branch"

    repository_client.create_branch(branch_name=branch_name, commit_msg="commit-1")

    # mypy false positive in lib due to getter/setter not being next to each other.
    assert any(
        branch
        for branch in upstream_git_repo.branches  # type: ignore
        if branch.name == branch_name
    )
    # Check files in the branch
    branch_files = set(
        upstream_git_repo.git.ls_tree("-r", branch_name, "--name-only").splitlines()
    )
    assert str(root_file) not in branch_files
    assert str(docs_file) in branch_files
    assert str(nested_docs_file) in branch_files


def test_create_branch_checkout_clash_default(
    repository_client: Client,
    repository_path: Path,
    upstream_git_repo: Repo,
    default_branch: str,
):
    """
    arrange: given Client and a file with the same name as the default branch and a file
        in the docs folder
    act: when _create_branch is called
    assert: a new branch is successfully created upstream with one or more files.
    """
    root_file = repository_path / default_branch
    root_file.write_text("content 1", encoding="utf-8")
    branch_name = "test-create-branch"
    docs_dir = Path(DOCUMENTATION_FOLDER_NAME)
    (repository_path / docs_dir).mkdir()
    docs_file = docs_dir / "test.txt"
    (repository_path / docs_file).write_text("content 2", encoding="utf-8")

    repository_client.create_branch(branch_name=branch_name, commit_msg="commit-1")

    assert upstream_git_repo.git.ls_tree("-r", branch_name, "--name-only")


def test_create_branch_checkout_clash_created(
    repository_client: Client, repository_path: Path, upstream_git_repo: Repo
):
    """
    arrange: given Client and a file with the same name as the requested branch and a
        file in the docs folder
    act: when _create_branch is called
    assert: a new branch is successfully created upstream with one or more files.
    """
    branch_name = "test-create-branch"
    root_file = repository_path / branch_name
    root_file.write_text("content 1", encoding="utf-8")
    docs_dir = Path(DOCUMENTATION_FOLDER_NAME)
    (repository_path / docs_dir).mkdir()
    docs_file = docs_dir / "test.txt"
    (repository_path / docs_file).write_text("content 2", encoding="utf-8")

    repository_client.create_branch(branch_name=branch_name, commit_msg="commit-1")

    assert upstream_git_repo.git.ls_tree("-r", branch_name, "--name-only")


def test_create_pull_request_error(monkeypatch: pytest.MonkeyPatch, repository_client: Client):
    """
    arrange: given Client with a mocked github repository client that raises an exception
    act: when _create_pull_request is called
    assert: RepositoryClientError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.create_pull.side_effect = [
        GithubException(status=500, data="Internal Server Error", headers=None)
    ]
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.create_pull_request(branch_name="branchname-1")

    assert_substrings_in_string(
        ("unexpected error creating pull request", "githubexception"), str(exc.value).lower()
    )


def test_create_pull_request(repository_client: Client, mock_pull_request: PullRequest):
    """
    arrange: given Client with a mocked github client that returns a mocked pull request
    act: when _create_pull_request is called
    assert: a pull request's page link is returned.
    """
    returned_url = repository_client.create_pull_request("branchname-1")

    assert returned_url == mock_pull_request.html_url


@pytest.mark.parametrize(
    "method",
    [
        pytest.param("get_git_ref", id="get_git_ref"),
        pytest.param("create_git_tag", id="create_git_tag"),
        pytest.param("create_git_ref", id="create_git_ref"),
    ],
)
def test_tag_commit_tag_github_error(
    method: str, monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given tag name and commit sha, Client with a mocked github repository client where a
        given method raises GithubException
    act: when tag_commit is called with the tag name and commit sha
    assert: RepositoryClientError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    getattr(mock_github_repository, method).side_effect = GithubException(
        status=401, data="Unauthorized", headers=None
    )
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.tag_commit(tag_name="tag 1", commit_sha="sha 1")

    assert_substrings_in_string(("unauthorized", "401"), str(exc.value).lower())


def test_tag_commit_tag_delete_tag_github_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given tag name and commit sha, Client with a mocked github repository client where a
        deleting a tag raises GithubException
    act: when tag_commit is called with the tag name and commit sha
    assert: RepositoryClientError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.get_git_ref.return_value.delete.side_effect = GithubException(
        status=401, data="Unauthorized", headers=None
    )
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.tag_commit(tag_name="tag 1", commit_sha="sha 1")

    assert_substrings_in_string(("unauthorized", "401"), str(exc.value).lower())


def test_tag_commit_tag_not_exists(monkeypatch: pytest.MonkeyPatch, repository_client: Client):
    """
    arrange: given tag name and commit sha, Client with a mocked github repository client where
        retrieving the tag raises UnknownObjectException
    act: when tag_commit is called with the tag name and commit sha
    assert: then the functions are called to create the tag.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.get_git_ref.side_effect = UnknownObjectException(
        status=404, data="Tag not found error", headers=None
    )
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)
    tag_name = "tag 1"
    commit_sha = "sha 1"

    repository_client.tag_commit(tag_name=tag_name, commit_sha=commit_sha)

    mock_github_repository.get_git_ref.assert_called_once_with(f"tags/{tag_name}")
    mock_github_repository.get_git_ref.return_value.delete.assert_not_called()

    mock_github_repository.create_git_tag.assert_called_once_with(
        tag_name, repository.TAG_MESSAGE, commit_sha, "commit"
    )
    mock_github_repository.create_git_ref.assert_called_once_with(
        f"refs/tags/{tag_name}", mock_github_repository.create_git_tag.return_value.sha
    )


def test_tag_commit_tag_exists(monkeypatch: pytest.MonkeyPatch, repository_client: Client):
    """
    arrange: given tag name and commit sha, Client with a mocked github repository client
    act: when tag_commit is called with the tag name and commit sha
    assert: then the functions are called to create the tag.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)
    tag_name = "tag 1"
    commit_sha = "sha 1"

    repository_client.tag_commit(tag_name=tag_name, commit_sha=commit_sha)

    mock_github_repository.get_git_ref.assert_called_once_with(f"tags/{tag_name}")
    mock_github_repository.get_git_ref.return_value.delete.assert_called_once_with()

    mock_github_repository.create_git_tag.assert_called_once_with(
        tag_name, repository.TAG_MESSAGE, commit_sha, "commit"
    )
    mock_github_repository.create_git_ref.assert_called_once_with(
        f"refs/tags/{tag_name}", mock_github_repository.create_git_tag.return_value.sha
    )


def test_get_file_content_from_tag_tag_github_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given Client with a mocked github repository client that raises an exception during
        tag operations
    act: when get_file_content_from_tag is called
    assert: RepositoryClientError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.get_git_ref.side_effect = GithubException(
        status=401, data="unauthorized", headers=None
    )
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.get_file_content_from_tag(path="path 1", tag_name="tag 1")

    assert_substrings_in_string(("unauthorized", "401"), str(exc.value).lower())


def test_get_file_content_from_tag_tag_unknown_object_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given Client with a mocked github repository client that raises an
        UnknownObjectException exception during tag operations
    act: when get_file_content_from_tag is called
    assert: RepositoryFileNotFoundError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.get_git_ref.side_effect = UnknownObjectException(
        status=404, data="File not found error", headers=None
    )
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)
    tag_name = "tag 1"

    with pytest.raises(RepositoryTagNotFoundError) as exc:
        repository_client.get_file_content_from_tag(path="path 1", tag_name=tag_name)

    assert_substrings_in_string(("not", "retrieve", "tag", tag_name), str(exc.value).lower())


def test_get_file_content_from_tag_content_github_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given Client with a mocked github repository client that raises an exception during
        content operations
    act: when get_file_content_from_tag is called
    assert: RepositoryClientError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.get_contents.side_effect = GithubException(
        status=401, data="unauthorized", headers=None
    )
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.get_file_content_from_tag(path="path 1", tag_name="tag 1")

    assert_substrings_in_string(("unauthorized", "401"), str(exc.value).lower())


def test_get_file_content_from_tag_unknown_object_error(
    monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given Client with a mocked github repository client that raises an
        UnknownObjectException exception during content operations
    act: when get_file_content_from_tag is called
    assert: RepositoryFileNotFoundError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.get_contents.side_effect = UnknownObjectException(
        status=404, data="File not found error", headers=None
    )
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)
    tag_name = "tag 1"
    path = "path 1"

    with pytest.raises(RepositoryFileNotFoundError) as exc:
        repository_client.get_file_content_from_tag(path=path, tag_name=tag_name)

    assert_substrings_in_string(
        ("not", "retrieve", "file", tag_name, path), str(exc.value).lower()
    )


def test_get_file_content_from_tag_list(
    monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given Client with a mocked github repository client that returns a list
    act: when get_file_content_from_tag is called
    assert: RepositoryFileNotFoundError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.get_contents.return_value = []
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)
    tag_name = "tag 1"
    path = "path 1"

    with pytest.raises(RepositoryFileNotFoundError) as exc:
        repository_client.get_file_content_from_tag(path=path, tag_name=tag_name)

    assert_substrings_in_string(
        ("path", "matched", "more", "file", tag_name, path), str(exc.value).lower()
    )


def test_get_file_content_from_tag_content_none(
    monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given Client with a mocked github repository client that returns None
        content
    act: when get_file_content_from_tag is called
    assert: RepositoryFileNotFoundError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_content_file = mock.MagicMock(spec=ContentFile)
    mock_content_file.content = None
    mock_github_repository.get_contents.return_value = mock_content_file
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)
    tag_name = "tag 1"
    path = "path 1"

    with pytest.raises(RepositoryFileNotFoundError) as exc:
        repository_client.get_file_content_from_tag(path=path, tag_name=tag_name)

    assert_substrings_in_string(("path", "not", "file", path, tag_name), str(exc.value).lower())


def test_get_file_content_from_tag(monkeypatch: pytest.MonkeyPatch, repository_client: Client):
    """
    arrange: given path, tag name, Client with a mocked github repository client that returns
        content
    act: when get_file_content_from_tag is called with the path and tag name
    assert: then the content is returned.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_content_file = mock.MagicMock(spec=ContentFile)
    content = "content 1"
    mock_content_file.content = base64.b64encode(content.encode(encoding="utf-8"))
    mock_github_repository.get_contents.return_value = mock_content_file
    monkeypatch.setattr(repository_client, "_github_repo", mock_github_repository)
    tag_name = "tag 1"
    path = "path 1"

    returned_content = repository_client.get_file_content_from_tag(path=path, tag_name=tag_name)

    assert returned_content == content
    mock_github_repository.get_git_ref.assert_called_once_with(f"tags/{tag_name}")
    mock_github_repository.get_git_tag.assert_called_once_with(
        mock_github_repository.get_git_ref.return_value.object.sha
    )
    mock_github_repository.get_contents.assert_called_once_with(
        path, mock_github_repository.get_git_tag.return_value.object.sha
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
    assert: InputError is raised.
    """
    with pytest.raises(InputError) as exc:
        repository._get_repository_name_from_git_url(remote_url=remote_url)

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
        repository._get_repository_name_from_git_url(remote_url=remote_url)
        == expected_repository_name
    )


def test_create_repository_client_no_token(
    repository_path: Path,
):
    """
    arrange: given valid repository path and empty access_token
    act: when create_repository_client is called
    assert: InputError is raised.
    """
    # the following token is deliberately empty for this test
    test_token = ""  # nosec

    with pytest.raises(InputError) as exc:
        repository.create_repository_client(access_token=test_token, base_path=repository_path)

    assert_substrings_in_string(
        ("invalid", "access_token", "input", "it must be", "non-empty"),
        str(exc.value).lower(),
    )


def test_create_repository_client(
    monkeypatch: pytest.MonkeyPatch,
    git_repo: Repo,
    repository_path: Path,
    mock_github_repo: Repository,
):
    """
    arrange: given valid repository path and a valid access_token and a mocked github client
    act: when create_repository_client is called
    assert: RepositoryClient is returned.
    """
    # The origin is initialised to be local, need to update it to be remote
    origin = git_repo.remote("origin")
    git_repo.delete_remote(origin)
    git_repo.create_remote("origin", "https://github.com/test-user/test-repo.git")
    test_token = secrets.token_hex(16)
    mock_github_client = mock.MagicMock(spec=Github)
    mock_github_client.get_repo.returns = mock_github_repo
    monkeypatch.setattr(repository, "Github", mock_github_client)

    returned_client = repository.create_repository_client(
        access_token=test_token, base_path=repository_path
    )

    assert isinstance(returned_client, repository.Client)
