# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for commit module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path

from src import commit
from src.constants import DEFAULT_BRANCH
from src.repository import Client


def test_parse_git_show_empty():
    """
    arrange: given empty show output
    act: when output is passed to parse_git_show
    assert: then no files are returned.
    """
    show_output = ""

    commit_files = tuple(commit.parse_git_show(show_output, repository_path=Path()))

    assert not commit_files


def test_parse_git_show_unsupported():
    """
    arrange: given show output that includes a line with a file with unknown status
    act: when output is passed to parse_git_show
    assert: then no files are returned.
    """
    show_output = "X    file.text"

    commit_files = tuple(commit.parse_git_show(show_output, repository_path=Path()))

    assert not commit_files


def test_parse_git_show_added(repository_client: Client):
    """
    arrange: given git repository
    act: when a file is added and show is called and the output passed to parse_git_show
    assert: then FileAdded is returned.
    """
    repository_path = repository_client.base_path
    (repository_path / (file := Path("file.text"))).write_text(
        contents := "content 1", encoding="utf-8"
    )
    branch_name = "test-add-branch"
    repository_client.switch(DEFAULT_BRANCH).create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=False, directory=None)
    show_output = repository_client._git_repo.git.show("--name-status")

    commit_files = tuple(commit.parse_git_show(show_output, repository_path=repository_path))

    assert len(commit_files) == 1
    commit_file = commit_files[0]
    assert commit_file.path == file
    assert isinstance(commit_file, commit.FileAddedOrModified)
    assert commit_file.content == contents


def test_parse_git_show_modified(repository_client: Client):
    """
    arrange: given git repository
    act: when a file is added and then modified and show is called and the output passed to
        parse_git_show
    assert: then FileModified is returned.
    """
    repository_path = repository_client.base_path
    (repository_path / (file := Path("file.text"))).write_text("content 1", encoding="utf-8")
    branch_name = "test-add-branch"
    repository_client.switch(DEFAULT_BRANCH).create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=False, directory=None)
    (repository_path / file).write_text(contents := "content 2", encoding="utf-8")
    repository_client.update_branch(commit_msg="commit-2", push=False, directory=None)
    show_output = repository_client._git_repo.git.show("--name-status")

    commit_files = tuple(commit.parse_git_show(show_output, repository_path=repository_path))

    assert len(commit_files) == 1
    commit_file = commit_files[0]
    assert commit_file.path == file
    assert isinstance(commit_file, commit.FileAddedOrModified)
    assert commit_file.content == contents


def test_parse_git_show_deleted(repository_client: Client):
    """
    arrange: given git repository
    act: when a file is added and then deleted and show is called and the output passed to
        parse_git_show
    assert: then FileDeleted is returned.
    """
    repository_path = repository_client.base_path
    (repository_path / (file := Path("file.text"))).write_text("content 1", encoding="utf-8")
    branch_name = "test-add-branch"
    repository_client.switch(DEFAULT_BRANCH).create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=False, directory=None)
    (repository_path / file).unlink()
    repository_client.update_branch(commit_msg="commit-2", push=False, directory=None)
    show_output = repository_client._git_repo.git.show("--name-status")

    commit_files = tuple(commit.parse_git_show(show_output, repository_path=repository_path))

    assert len(commit_files) == 1
    commit_file = commit_files[0]
    assert commit_file.path == file
    assert isinstance(commit_file, commit.FileDeleted)


def test_parse_git_show_renamed(repository_client: Client):
    """
    arrange: given git repository
    act: when a file is added and then renamed and show is called and the output passed to
        parse_git_show
    assert: then FileDeleted and FileAdded is returned.
    """
    repository_path = repository_client.base_path
    (repository_path / (file := Path("file.text"))).write_text(
        contents := "content 1", encoding="utf-8"
    )
    branch_name = "test-add-branch"
    repository_client.switch(DEFAULT_BRANCH).create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=False, directory=None)
    (repository_path / file).rename(repository_path / (new_file := Path("other_file.text")))
    repository_client.update_branch(commit_msg="commit-2", push=False, directory=None)
    show_output = repository_client._git_repo.git.show("--name-status")

    commit_files = tuple(commit.parse_git_show(show_output, repository_path=repository_path))

    assert len(commit_files) == 2
    commit_file_delete = commit_files[0]
    assert commit_file_delete.path == file
    assert isinstance(commit_file_delete, commit.FileDeleted)
    commit_file_add = commit_files[1]
    assert commit_file_add.path == new_file
    assert isinstance(commit_file_add, commit.FileAddedOrModified)
    assert commit_file_add.content == contents


def test_parse_git_show_copied(repository_client: Client):
    """
    arrange: given git repository
    act: when a file is added and then renamed and show is called and the output modified to copied
        and passed to parse_git_show
    assert: then FileAdded is returned.
    """
    repository_path = repository_client.base_path
    (repository_path / (file := Path("file.text"))).write_text(
        contents := "content 1", encoding="utf-8"
    )
    branch_name = "test-add-branch"
    repository_client.switch(DEFAULT_BRANCH).create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=False, directory=None)
    (repository_path / file).rename(repository_path / (new_file := Path("other_file.text")))
    repository_client.update_branch(commit_msg="commit-2", push=False, directory=None)
    show_output: str = repository_client._git_repo.git.show("--name-status")
    # Change renamed to copied, it isn't clear how to make git think a file was copied
    show_output = show_output.replace("R100", "C100")

    commit_files = tuple(commit.parse_git_show(show_output, repository_path=repository_path))

    assert len(commit_files) == 1
    commit_file = commit_files[0]
    assert commit_file.path == new_file
    assert isinstance(commit_file, commit.FileAddedOrModified)
    assert commit_file.content == contents


def test_parse_git_show_multiple(repository_client: Client):
    """
    arrange: given git repository
    act: when multiple files are added and show is called and the output passed to parse_git_show
    assert: then multiple FileAdded is returned.
    """
    repository_path = repository_client.base_path
    (repository_path / (file_1 := Path("file_1.text"))).write_text(
        contents_1 := "content 1", encoding="utf-8"
    )
    (repository_path / (file_2 := Path("file_2.text"))).write_text(
        contents_2 := "content 2", encoding="utf-8"
    )
    branch_name = "test-add-branch"
    repository_client.switch(DEFAULT_BRANCH).create_branch(branch_name=branch_name).switch(
        branch_name
    ).update_branch(commit_msg="commit-1", push=False, directory=None)
    show_output = repository_client._git_repo.git.show("--name-status")

    commit_files = tuple(commit.parse_git_show(show_output, repository_path=repository_path))

    assert len(commit_files) == 2
    commit_file_1 = commit_files[1]
    assert commit_file_1.path == file_1
    assert isinstance(commit_file_1, commit.FileAddedOrModified)
    assert commit_file_1.content == contents_1
    commit_file_2 = commit_files[0]
    assert commit_file_2.path == file_2
    assert isinstance(commit_file_2, commit.FileAddedOrModified)
    assert commit_file_2.content == contents_2
