# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for git."""

import base64

# Need access to protected functions for testing
# pylint: disable=protected-access
import secrets
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest
from git import Git
from git.exc import GitCommandError
from git.repo import Repo
from github import Github
from github.ContentFile import ContentFile
from github.GithubException import GithubException, UnknownObjectException
from github.PullRequest import PullRequest
from github.Repository import Repository

from src import repository
from src.constants import DOCUMENTATION_FOLDER_NAME, DOCUMENTATION_TAG
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


def test_current_branch_switch_main(repository_client):
    """
    arrange: given a repository in a detached state
    act: we switch branch to main
    assert: current_branch should provide first the commit hash and then the main name
    """
    repository_client._git_repo.git.tag("-d", DOCUMENTATION_TAG)

    _hash = repository_client.current_branch

    repository_client.switch("main")

    assert repository_client.current_branch == "main"
    assert repository_client._git_repo.head.ref.commit.hexsha == _hash


def test_current_branch_switch_to_tag(repository_client):
    """
    arrange: given a repository in a detached state
    act: we first tag the commit and then switch to the tag
    assert: current_branch should provide first the commit hash and then the tag name
    """
    _hash = repository_client.current_branch

    repository_client._git_repo.git.tag("my-tag")

    assert repository_client.current_branch != _hash
    assert repository_client.current_branch == "my-tag"


def test_create_branch_error(monkeypatch: pytest.MonkeyPatch, repository_client: Client):
    """
    arrange: given Client with a mocked local git repository that raises an exception
    act: when _create_branch is called
    assert: RepositoryClientError is raised.
    """
    err_str = "mocked error"
    mock_git_repository = mock.MagicMock(spec=Repo)
    mock_git_repository.git.branch.side_effect = [GitCommandError(err_str)]
    monkeypatch.setattr(repository_client, "_git_repo", mock_git_repository)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.switch("main").create_branch(branch_name="test-create-branch")

    assert_substrings_in_string(
        ("unexpected error creating new branch", err_str), str(exc.value).lower()
    )


def test_create_branch(
    repository_client: Client,
    upstream_git_repo: Repo,
):
    """
    arrange: given Client and newly created files in `repo` and `repo/docs` directories
    act: when _create_branch is called
    assert: a new branch is successfully created upstream with only the files in the `repo/docs`
        directory.
    """
    repository_path = repository_client.base_path

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

    repository_client.switch("main").create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=True)

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
    upstream_git_repo: Repo,
    default_branch: str,
):
    """
    arrange: given Client and a file with the same name as the default branch and a file
        in the docs folder
    act: when _create_branch is called
    assert: a new branch is successfully created upstream with one or more files.
    """
    repository_path = repository_client.base_path

    root_file = repository_path / default_branch
    root_file.write_text("content 1", encoding="utf-8")
    branch_name = "test-create-branch"
    docs_dir = Path(DOCUMENTATION_FOLDER_NAME)
    (repository_path / docs_dir).mkdir()
    docs_file = docs_dir / "test.txt"
    (repository_path / docs_file).write_text("content 2", encoding="utf-8")

    repository_client.switch("main").create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=True)

    assert upstream_git_repo.git.ls_tree("-r", branch_name, "--name-only")


def test_create_branch_checkout_clash_created(repository_client: Client, upstream_git_repo: Repo):
    """
    arrange: given Client and a file with the same name as the requested branch and a
        file in the docs folder
    act: when _create_branch is called
    assert: a new branch is successfully created upstream with one or more files.
    """
    repository_path = repository_client.base_path

    branch_name = "test-create-branch"
    root_file = repository_path / branch_name
    root_file.write_text("content 1", encoding="utf-8")
    docs_dir = Path(DOCUMENTATION_FOLDER_NAME)
    (repository_path / docs_dir).mkdir()
    docs_file = docs_dir / "test.txt"
    (repository_path / docs_file).write_text("content 2", encoding="utf-8")

    repository_client.switch("main").create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=True)

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
    "get_method",
    [
        pytest.param(
            lambda mock_github_repository: mock_github_repository.get_git_ref, id="get_git_ref"
        ),
        pytest.param(
            lambda mock_github_repository: mock_github_repository.create_git_tag,
            id="create_git_tag",
        ),
        pytest.param(
            lambda mock_github_repository: mock_github_repository.create_git_ref,
            id="create_git_ref",
        ),
        pytest.param(
            lambda mock_github_repository: mock_github_repository.get_git_ref.return_value.delete,
            id="get_git_ref.return_value.delete",
        ),
    ],
)
def test_tag_commit_tag_github_error(
    get_method: Callable[[Repository], mock.MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    repository_client: Client,
):
    """
    arrange: given tag name and commit sha, Client with a mocked github repository client where a
        given method raises GithubException
    act: when tag_commit is called with the tag name and commit sha
    assert: RepositoryClientError is raised.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    get_method(mock_github_repository).side_effect = GithubException(
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
    assert: then the functions are called to delete the pre-existing and create the new tag.
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


def test_get_file_content_from_tag_commit_tag(
    monkeypatch: pytest.MonkeyPatch, repository_client: Client
):
    """
    arrange: given path, tag name, Client with a mocked github repository client that returns
        content and tag that is a commit tag
    act: when get_file_content_from_tag is called with the path and tag name
    assert: then the content is returned.
    """
    mock_github_repository = mock.MagicMock(spec=Repository)
    mock_github_repository.get_git_ref.return_value.object.type = "commit"
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
    mock_github_repository.get_git_tag.assert_not_called()
    mock_github_repository.get_contents.assert_called_once_with(
        path, mock_github_repository.get_git_ref.return_value.object.sha
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
    git_repo_with_remote: Repo,
    repository_path: Path,
    mock_github_repo: Repository,
):
    """
    arrange: given valid repository path and a valid access_token and a mocked github client
    act: when create_repository_client is called
    assert: RepositoryClient is returned.
    """
    _ = git_repo_with_remote

    test_token = secrets.token_hex(16)
    mock_github_client = mock.MagicMock(spec=Github)
    mock_github_client.get_repo.returns = mock_github_repo
    monkeypatch.setattr(repository, "Github", mock_github_client)

    returned_client = repository.create_repository_client(
        access_token=test_token, base_path=repository_path
    )

    assert isinstance(returned_client, repository.Client)


def test_repository_summary_modified(repository_client):
    """
    arrange: given repository with a modified file with respect to the head
    act: when summary is called
    assert: The DiffSummary object represents the modified file.
    """
    (repository_client.base_path / "file-1.txt").write_text("My first version")
    repository_client.update_branch("file-1 commit", force=False, push=False)

    assert len(repository_client.summary.modified) == 0

    (repository_client.base_path / "file-1.txt").write_text("My second version")

    assert len(repository_client.summary.modified) == 1
    assert list(repository_client.summary.modified)[0] == "file-1.txt"


def test_repository_summary_new(repository_client):
    """
    arrange: given repository with a new file with respect to the head
    act: when summary is called
    assert: The DiffSummary object represents the new file.
    """
    (repository_client.base_path / "file-1.txt").write_text("My first version")
    repository_client.update_branch("file-1 commit", force=False, push=False)

    assert len(repository_client.summary.new) == 0

    (repository_client.base_path / "file-2.txt").write_text("My second version")

    assert len(repository_client.summary.new) == 1
    assert list(repository_client.summary.new)[0] == "file-2.txt"


def test_repository_summary_remove(repository_client):
    """
    arrange: given repository with a removed file with respect to the head
    act: when summary is called
    assert: The DiffSummary object represents the remove file.
    """
    (repository_client.base_path / "file-1.txt").write_text("My first version")
    repository_client.update_branch("file-1 commit", force=False, push=False)

    assert len(repository_client.summary.removed) == 0

    (repository_client.base_path / "file-1.txt").unlink()

    assert len(repository_client.summary.removed) == 1
    assert list(repository_client.summary.removed)[0] == "file-1.txt"


def test_repository_summary_invalid_operation(repository_client):
    """
    arrange: given repository
    act: when summary is added to a non DiffSummary object
    assert: an exception ValueError is raised.
    """
    with pytest.raises(ValueError):
        _ = repository_client.summary + 1.0


def test_repository_pull_default_branch(
    repository_client, upstream_git_repo, upstream_repository_path
):
    """
    arrange: given repository with an updated upstream
    act: when the pull method of the repository is called
    assert: the new commits are pulled from the upstream
    """
    branch_name = "main"

    repository_client.switch(branch_name)

    (repository_client.base_path / "filler-file-1").touch()

    repository_client.update_branch("commit 1")

    upstream_git_repo.git.checkout(branch_name)
    first_hash = upstream_git_repo.head.ref.commit.hexsha
    (upstream_repository_path / "filler-file-2").touch()
    upstream_git_repo.git.add(".")
    upstream_git_repo.git.commit("-m", "test")
    second_hash = upstream_git_repo.head.ref.commit.hexsha

    assert repository_client._git_repo.head.ref.commit.hexsha == first_hash
    repository_client.pull()
    assert repository_client._git_repo.head.ref.commit.hexsha == second_hash


def test_repository_pull_other_branch(
    repository_client, upstream_git_repo, upstream_repository_path
):
    """
    arrange: given repository with an updated upstream
    act: when the pull method of the repository is called from a different branch
    assert: the new commits are pulled from the upstream in the not-checkout branch
    """
    branch_name = "other-branch"

    repository_client.create_branch(branch_name).switch(branch_name)

    (repository_client.base_path / "filler-file-1").touch()

    repository_client.update_branch("commit 1")

    upstream_git_repo.git.checkout(branch_name)
    first_hash = upstream_git_repo.head.ref.commit.hexsha
    (upstream_repository_path / "filler-file-2").touch()
    upstream_git_repo.git.add(".")
    upstream_git_repo.git.commit("-m", "test")
    second_hash = upstream_git_repo.head.ref.commit.hexsha

    assert repository_client._git_repo.head.ref.commit.hexsha == first_hash
    repository_client.switch("main").pull(branch_name)
    assert repository_client._git_repo.head.ref.commit.hexsha != second_hash
    repository_client.switch(branch_name)
    assert repository_client._git_repo.head.ref.commit.hexsha == second_hash


def test_switch_branch_pop_error(monkeypatch, repository_client: Client):
    """
    arrange: given Client with a mocked local git repository client that raises an
        exception when getting stashes deltas (pop)
    act: when switch branch is called
    assert: RepositoryClientError is raised from GitCommandError.
    """

    def side_effect(*args):
        """Mock function.

        Args:
            args: positional arguments

        Raises:
            GitCommandError: when providing pop
        """
        if args and args[0] == "pop":
            raise GitCommandError("mocked error")

    mock_git_repository = mock.MagicMock(spec=Git)
    mock_git_repository.add = mock.Mock(return_value=None)
    mock_git_repository.stash = mock.Mock(side_effect=side_effect)
    monkeypatch.setattr(repository_client._git_repo, "git", mock_git_repository)
    monkeypatch.setattr(repository_client._git_repo, "is_dirty", lambda *args, **kwargs: True)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.switch("branchname-1")

    assert_substrings_in_string(
        ("unexpected error when switching branch to branchname-1"), str(exc.value).lower()
    )


def test_update_branch_unknown_error(monkeypatch, repository_client: Client):
    """
    arrange: given Client with a mocked local git repository client that raises an
        exception when pushing commits
    act: when update branch is called
    assert: RepositoryClientError is raised from GitCommandError.
    """
    repository_client.switch("main")

    def side_effect(*args):
        """Mock function.

        Args:
            args: positional arguments

        Raises:
            GitCommandError: when providing pop
        """
        raise GitCommandError("mocked error")

    mock_git_repository = mock.MagicMock(spec=Git)
    mock_git_repository.add = mock.Mock(return_value=None)
    mock_git_repository.commit = mock.Mock(return_value=None)
    mock_git_repository.push = mock.Mock(side_effect=side_effect)
    monkeypatch.setattr(repository_client._git_repo, "git", mock_git_repository)
    monkeypatch.setattr(repository_client._git_repo, "is_dirty", lambda *args, **kwargs: True)

    with pytest.raises(RepositoryClientError) as exc:
        repository_client.update_branch("my-message")

    assert_substrings_in_string(("unexpected error updating branch"), str(exc.value).lower())


def test_get_single_pull_request(monkeypatch, repository_client: Client, mock_pull_request):
    """
    arrange: given Client with a mocked local github client that mock an existing pull request on
        branch "main"
    act: when get repository get_pull_request method is called with the branch main
    assert: that the method returns the pull-request url.
    """
    mock_git_repository = mock.MagicMock(spec=Repository)
    mock_git_repository.get_pulls = mock.Mock(return_value=[mock_pull_request])
    monkeypatch.setattr(repository_client, "_github_repo", mock_git_repository)

    pull_request_link = repository_client.get_pull_request("main")

    assert pull_request_link is not None
    assert pull_request_link == "test_url"


def test_get_non_existing_pull_request(monkeypatch, repository_client: Client, mock_pull_request):
    """
    arrange: given Client with a mocked local github client that mock an existing pull request on
        branch "main"
    act: when get repository get_pull_request is called with another branch other than main
    assert: that None is return.
    """
    mock_git_repository = mock.MagicMock(spec=Repository)
    mock_git_repository.get_pulls = mock.Mock(return_value=[mock_pull_request])
    monkeypatch.setattr(repository_client, "_github_repo", mock_git_repository)

    pull_request_link = repository_client.get_pull_request("not-existing")

    assert pull_request_link is None


def test_get_multiple_pull_request_error(
    monkeypatch, repository_client: Client, mock_pull_request
):
    """
    arrange: given Client with a mocked local github client that mock an condition where
        multiple pull request for branch "main" exists
    act: when get repository get_pull_request is called with branch main
    assert: an exception is returned
    """
    mock_git_repository = mock.MagicMock(spec=Repository)
    mock_git_repository.get_pulls = mock.Mock(return_value=[mock_pull_request, mock_pull_request])
    monkeypatch.setattr(repository_client, "_github_repo", mock_git_repository)

    with pytest.raises(RepositoryClientError) as exc:
        _ = repository_client.get_pull_request("main")

    assert_substrings_in_string(("more than one open pull request"), str(exc.value).lower())
