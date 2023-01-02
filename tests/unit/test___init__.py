# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for execution."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from unittest import mock

import pytest
from git.repo import Repo
from github.PullRequest import PullRequest
from github.Repository import Repository

from src import (
    DOCUMENTATION_FOLDER_NAME,
    GETTING_STARTED,
    _run_migrate,
    _run_reconcile,
    discourse,
    exceptions,
    index,
    metadata,
    pull_request,
    reconcile,
    run,
    types_,
)

from .helpers import create_metadata_yaml


def test__run_reconcile_empty_local_server(tmp_path: Path):
    """
    arrange: given metadata with name but not docs and empty docs folder and mocked discourse
    act: when _run_reconcile is called
    assert: then an index page is created with empty navigation table.
    """
    meta = types_.Metadata(name="name 1", docs=None)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.return_value = (url := "url 1")

    returned_page_interactions = _run_reconcile(
        base_path=tmp_path,
        metadata=meta,
        discourse=mocked_discourse,
        dry_run=False,
        delete_pages=True,
    )

    mocked_discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{reconcile.NAVIGATION_TABLE_START.strip()}",
    )
    assert returned_page_interactions == {url: types_.ActionResult.SUCCESS}


def test__run_reconcile_local_empty_server(tmp_path: Path):
    """
    arrange: given metadata with name but not docs and docs folder with a file and mocked discourse
    act: when _run_reconcile is called
    assert: then a documentation page is created and an index page is created with a navigation
        page with a reference to the documentation page.
    """
    name = "name 1"
    meta = types_.Metadata(name=name, docs=None)
    (docs_folder := tmp_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_content := "index content")
    (docs_folder / "page.md").write_text(page_content := "page content")
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.side_effect = [
        (page_url := "url 1"),
        (index_url := "url 2"),
    ]

    returned_page_interactions = _run_reconcile(
        base_path=tmp_path,
        metadata=meta,
        discourse=mocked_discourse,
        dry_run=False,
        delete_pages=True,
    )

    assert mocked_discourse.create_topic.call_count == 2
    mocked_discourse.create_topic.assert_any_call(
        title=f"{name} docs: {page_content}", content=page_content
    )
    mocked_discourse.create_topic.assert_any_call(
        title="Name 1 Documentation Overview",
        content=(
            f"{index_content}{reconcile.NAVIGATION_TABLE_START}\n"
            f"| 1 | page | [{page_content}]({page_url}) |"
        ),
    )
    assert returned_page_interactions == {
        page_url: types_.ActionResult.SUCCESS,
        index_url: types_.ActionResult.SUCCESS,
    }


def test__run_reconcile_local_empty_server_dry_run(tmp_path: Path):
    """
    arrange: given metadata with name but not docs and docs folder with a file and mocked discourse
    act: when _run_reconcile is called with dry run mode enabled
    assert: no pages are created.
    """
    meta = types_.Metadata(name="name 1", docs=None)
    (docs_folder := tmp_path / "docs").mkdir()
    (docs_folder / "index.md").write_text("index content")
    (docs_folder / "page.md").write_text("page content")
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)

    returned_page_interactions = _run_reconcile(
        base_path=tmp_path,
        metadata=meta,
        discourse=mocked_discourse,
        dry_run=True,
        delete_pages=True,
    )

    mocked_discourse.create_topic.assert_not_called()
    assert not returned_page_interactions


def test__run_reconcile_local_empty_server_error(tmp_path: Path):
    """
    arrange: given metadata with name but not docs and empty docs directory and mocked discourse
        that raises an exception
    act: when _run_reconcile is called
    assert: no pages are created.
    """
    meta = types_.Metadata(name="name 1", docs=None)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.side_effect = exceptions.DiscourseError

    returned_page_interactions = _run_reconcile(
        base_path=tmp_path,
        metadata=meta,
        discourse=mocked_discourse,
        dry_run=False,
        delete_pages=True,
    )

    mocked_discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{reconcile.NAVIGATION_TABLE_START.strip()}",
    )
    assert not returned_page_interactions


def test__run_migrate_server_error_index(tmp_path: Path, repository: tuple[Repo, Path]):
    """
    arrange: given metadata with name and docs but no docs directory and mocked discourse
        that raises an exception during index file fetching
    act: when _run_migrate is called
    assert: Server error is raised with page retrieval fail.
    """
    meta = types_.Metadata(name="name 1", docs="http://discourse/t/docs")
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = [exceptions.DiscourseError]
    mocked_github_repo = mock.MagicMock(spec=Repository)
    (repo, _) = repository

    with pytest.raises(exceptions.ServerError) as exc:
        _run_migrate(
            base_path=tmp_path,
            metadata=meta,
            discourse=mocked_discourse,
            repo=repo,
            github_repo=mocked_github_repo,
            branch_name=None,
            dry_run=False,
        )

    assert "Index page retrieval failed" == str(exc.value)


def test__run_migrate_server_error_topic(
    repository: tuple[Repo, Path],
    mock_github_repo: Repository,
):
    """
    arrange: given metadata with name and docs but no docs directory and mocked discourse
        that raises an exception during topic retrieval
    act: when _run_migrate is called
    assert: MigrationError is raised.
    """
    index_url = "http://discourse/t/docs"
    index_content = """Content Title

    Content description.

    # Navigation

    | Level | Path | Navlink |
    | -- | -- | -- |
    | 1 | path-1 | [Link](/t/link-to-1) |
    """
    meta = types_.Metadata(name="name 1", docs=index_url)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = [index_content, exceptions.DiscourseError]
    (repo, repo_path) = repository

    with pytest.raises(exceptions.MigrationError):
        _run_migrate(
            base_path=repo_path,
            metadata=meta,
            discourse=mocked_discourse,
            repo=repo,
            github_repo=mock_github_repo,
            branch_name=None,
            dry_run=False,
        )


# pylint: disable=too-many-locals
def test__run_migrate(
    repository: tuple[Repo, Path],
    upstream_repository: tuple[Repo, Path],
    mock_pull_request: PullRequest,
    mock_github_repo: Repository,
):
    """
    arrange: given metadata with name and docs but no docs directory and mocked discourse
    act: when _run_migrate is called
    assert: docs are migrated and a report on migrated documents are returned.
    """
    index_content = """Content header.

    Content body."""
    index_table = f"""{index.NAVIGATION_TABLE_START}
    | 1 | path-1 | [Tutorials](link-1) |"""
    index_page = f"{index_content}{index_table}"
    meta = types_.Metadata(name="name 1", docs="http://discourse/t/docs")
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = [
        index_page,
        (link_content := "link 1 content"),
    ]
    (repo, repo_path) = repository

    returned_migration_reports = _run_migrate(
        base_path=repo_path,
        metadata=meta,
        discourse=mocked_discourse,
        repo=repo,
        github_repo=mock_github_repo,
        branch_name=None,
        dry_run=False,
    )

    (upstream_repo, upstream_path) = upstream_repository
    upstream_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert returned_migration_reports == {mock_pull_request.html_url: types_.ActionResult.SUCCESS}
    assert (index_file := upstream_path / DOCUMENTATION_FOLDER_NAME / "index.md").is_file()
    assert (path_file := upstream_path / DOCUMENTATION_FOLDER_NAME / "path-1.md").is_file()
    assert index_file.read_text(encoding="utf-8") == index_content
    assert path_file.read_text(encoding="utf-8") == link_content


# pylint: enable=too-many-locals


def test_run_no_docs_no_dir(repository: tuple[Repo, Path]):
    """
    arrange: given a path with a metadata.yaml that has no docs key and no docs directory
        and mocked discourse
    act: when run is called
    assert: InputError is raised with a guide to getting started.
    """
    (repo, repo_path) = repository
    # this is an access token string for testing purposes.
    test_access_token = "test-access-token"  # nosec
    create_metadata_yaml(content=f"{metadata.METADATA_NAME_KEY}: name 1", path=repo_path)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)

    with pytest.raises(exceptions.InputError) as exc:
        # run is repeated in unit tests / integration tests
        # pylint: disable=duplicate-code
        _ = run(
            base_path=repo_path,
            discourse=mocked_discourse,
            dry_run=False,
            delete_pages=False,
            repo=repo,
            github_access_token=test_access_token,
            branch_name=None,
        )

    assert str(exc.value) == GETTING_STARTED


def test_run_no_docs_empty_dir(repository: tuple[Repo, Path]):
    """
    arrange: given a path with a metadata.yaml that has no docs key and has empty docs directory
        and mocked discourse
    act: when run is called
    assert: then an index page is created with empty navigation table.
    """
    (repo, repo_path) = repository
    # this is an access token string for testing purposes.
    test_access_token = "test-access-token"  # nosec
    create_metadata_yaml(content=f"{metadata.METADATA_NAME_KEY}: name 1", path=repo_path)
    (repo_path / index.DOCUMENTATION_FOLDER_NAME).mkdir()
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.return_value = (url := "url 1")

    # run is repeated in unit tests / integration tests
    # pylint: disable=duplicate-code
    returned_page_interactions = run(
        base_path=repo_path,
        discourse=mocked_discourse,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token=test_access_token,
        branch_name=None,
    )

    mocked_discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{reconcile.NAVIGATION_TABLE_START.strip()}",
    )
    assert returned_page_interactions == {url: types_.ActionResult.SUCCESS}


# pylint: disable=too-many-locals
@pytest.mark.usefixtures("patch_get_repository_name", "patch_create_github")
def test_run_no_docs_dir(
    repository: tuple[Repo, Path],
    upstream_repository: tuple[Repo, Path],
    mock_pull_request: PullRequest,
):
    """
    arrange: given a path with a metadata.yaml that has docs key and no docs directory
        and mocked discourse
    act: when run is called
    assert: then docs from the server is migrated into local docs path and the files created
        are return as the result.
    """
    (repo, repo_path) = repository
    # this is an access token string for testing purposes.
    test_access_token = "test-access-token"  # nosec
    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: name 1\n" f"{metadata.METADATA_DOCS_KEY}: docsUrl",
        path=repo_path,
    )
    index_content = """Content header.

    Content body.\n"""
    index_table = f"""{index.NAVIGATION_TABLE_START}
    | 1 | path-1 | [empty-navlink]() |
    | 2 | file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = [index_page, navlink_page]

    # run is repeated in unit tests / integration tests
    # pylint: disable=duplicate-code
    returned_migration_reports = run(
        base_path=repo_path,
        discourse=mocked_discourse,
        dry_run=False,
        delete_pages=False,
        repo=repo,
        github_access_token=test_access_token,
        branch_name=None,
    )
    # pylint: enable=duplicate-code

    (upstream_repo, upstream_path) = upstream_repository
    upstream_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert returned_migration_reports == {mock_pull_request.html_url: types_.ActionResult.SUCCESS}
    assert (index_file := upstream_path / DOCUMENTATION_FOLDER_NAME / "index.md").is_file()
    assert (
        path_file := upstream_path / DOCUMENTATION_FOLDER_NAME / "path-1" / "file-1.md"
    ).is_file()
    assert index_file.read_text(encoding="utf-8") == index_content
    assert path_file.read_text(encoding="utf-8") == navlink_page
