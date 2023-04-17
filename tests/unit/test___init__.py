# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for execution."""
import logging
from pathlib import Path
from unittest import mock

import pytest
from git.repo import Repo
from github.PullRequest import PullRequest

from src import (  # GETTING_STARTED,
    DOCUMENTATION_FOLDER_NAME,
    DOCUMENTATION_TAG,
    Clients,
    constants,
    discourse,
    exceptions,
    get_clients,
    pull_request,
    run_migrate,
    run_reconcile,
    types_,
)
from src.metadata import METADATA_DOCS_KEY, METADATA_NAME_KEY

from .. import factories
from ..conftest import BASE_REMOTE_BRANCH
from .helpers import assert_substrings_in_string, create_metadata_yaml

# Need access to protected functions for testing
# pylint: disable=protected-access


@mock.patch("github.Github.get_repo")
def test_setup_clients(get_repo_mock, git_repo_with_remote):
    """
    arrange: given a local path and user_inputs
    act: when get_clients is called
    assert: then the Discourse and RepositoryClients are instantiated appropriately
    """
    get_repo_mock.return_value = git_repo_with_remote

    path = Path(git_repo_with_remote.working_dir)

    user_inputs = factories.UserInputsFactory()
    clients = get_clients(user_inputs=user_inputs, base_path=path)

    assert clients.repository.base_path == path

    assert clients.discourse._category_id == int(user_inputs.discourse.category_id)
    assert clients.discourse._base_path == f"https://{user_inputs.discourse.hostname}"
    assert clients.discourse._api_username == user_inputs.discourse.api_username
    assert clients.discourse._api_key == user_inputs.discourse.api_key


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_empty_local_server(mocked_clients):
    """
    arrange: given metadata with name but not docs and empty docs folder and mocked discourse
    act: when _run_reconcile is called
    assert: then an index page is created with empty navigation table.
    """
    mocked_clients.discourse.create_topic.return_value = (url := "url 1")

    user_inputs = factories.UserInputsFactory(dry_run=False, delete_pages=True)

    (mocked_clients.repository.base_path / "docs").mkdir()

    returned_page_interactions = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    mocked_clients.discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{constants.NAVIGATION_TABLE_START.strip()}",
    )
    assert returned_page_interactions == {url: types_.ActionResult.SUCCESS}


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_local_empty_server(mocked_clients):
    """
    arrange: given metadata with name but not docs and docs folder with a file and mocked discourse
    act: when _run_reconcile is called
    assert: then a documentation page is created and an index page is created with a navigation
        page with a reference to the documentation page.
    """
    name = mocked_clients.repository.metadata.name

    (docs_folder := mocked_clients.repository.base_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_content := "index content")
    (docs_folder / "page.md").write_text(page_content := "page content")
    mocked_clients.discourse.create_topic.side_effect = [
        (page_url := "url 1"),
        (index_url := "url 2"),
    ]
    user_inputs = factories.UserInputsFactory(dry_run=False, delete_pages=True)

    returned_page_interactions = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    assert mocked_clients.discourse.create_topic.call_count == 2
    mocked_clients.discourse.create_topic.assert_any_call(
        title=f"{name} docs: {page_content}", content=page_content
    )
    mocked_clients.discourse.create_topic.assert_any_call(
        title="Name 1 Documentation Overview",
        content=(
            f"{index_content}{constants.NAVIGATION_TABLE_START}\n"
            f"| 1 | page | [{page_content}]({page_url}) |"
        ),
    )
    assert returned_page_interactions == {
        page_url: types_.ActionResult.SUCCESS,
        index_url: types_.ActionResult.SUCCESS,
    }


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_local_empty_server_dry_run(mocked_clients):
    """
    arrange: given metadata with name but not docs and docs folder with a file and mocked discourse
    act: when _run_reconcile is called with dry run mode enabled
    assert: no pages are created.
    """
    (docs_folder := mocked_clients.repository.base_path / "docs").mkdir()
    (docs_folder / "index.md").write_text("index content")
    (docs_folder / "page.md").write_text("page content")
    user_inputs = factories.UserInputsFactory(dry_run=True, delete_pages=True)

    returned_page_interactions = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    mocked_clients.discourse.create_topic.assert_not_called()
    assert not returned_page_interactions


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_local_empty_server_dry_run_no_tag(mocked_clients):
    """
    arrange: given metadata with name but not docs and docs folder with a file and mocked discourse
        and the upload-docs-tag is destroyed before calling run_reconcile
    act: when _run_reconcile is called with dry run mode enabled
    assert: no pages are created.
    """
    (docs_folder := mocked_clients.repository.base_path / "docs").mkdir()
    (docs_folder / "index.md").write_text("index content")
    (docs_folder / "page.md").write_text("page content")
    user_inputs = factories.UserInputsFactory(dry_run=True, delete_pages=True)

    mocked_clients.repository._git_repo.git.tag("-d", DOCUMENTATION_TAG)

    returned_page_interactions = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    mocked_clients.discourse.create_topic.assert_not_called()
    assert not returned_page_interactions


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_local_empty_server_error(mocked_clients):
    """
    arrange: given metadata with name but not docs and empty docs directory and mocked discourse
        that raises an exception
    act: when _run_reconcile is called
    assert: no pages are created.
    """
    mocked_clients.discourse.create_topic.side_effect = exceptions.DiscourseError
    user_inputs = factories.UserInputsFactory(dry_run=False, delete_pages=True)

    (mocked_clients.repository.base_path / "docs").mkdir()

    returned_page_interactions = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    mocked_clients.discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{constants.NAVIGATION_TABLE_START.strip()}",
    )
    assert not returned_page_interactions


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="index-url"),
)
@mock.patch("src.repository.Client.get_file_content_from_tag")
def test__run_reconcile_local_server_conflict(mock_tag, mocked_clients):
    """
    arrange: given metadata with name and docs and docs folder with a file and mocked discourse
        with content that conflicts with the local content
    act: when _run_reconcile is called
    assert: InputError is raised.
    """
    repository_client = mocked_clients.repository

    (docs_folder := repository_client.base_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_content := "index content")
    main_page_content = "page content 1"
    (docs_folder / "page.md").write_text(local_page_content := "page content 2")
    page_url = "page-url"
    server_page_content = "page content 3"
    mocked_clients.discourse.retrieve_topic.side_effect = [
        (
            f"{index_content}{constants.NAVIGATION_TABLE_START}\n"
            f"| 1 | page | [{local_page_content}]({page_url}) |"
        ),
        server_page_content,
    ]
    mock_tag.return_value = main_page_content
    user_inputs = factories.UserInputsFactory(dry_run=False, delete_pages=True)

    with pytest.raises(exceptions.InputError) as exc_info:
        run_reconcile(
            clients=mocked_clients,
            user_inputs=user_inputs,
        )

    assert_substrings_in_string(("actions", "not", "executed"), str(exc_info.value))
    assert mocked_clients.discourse.retrieve_topic.call_count == 2
    mocked_clients.discourse.retrieve_topic.assert_any_call(url=repository_client.metadata.docs)
    mocked_clients.discourse.retrieve_topic.assert_any_call(url=page_url)


@mock.patch("src.repository.Client.metadata", types_.Metadata(name="name 1", docs=None))
def test__run_reconcile_no_docs(caplog, mocked_clients):
    """
    arrange: given metadata with name and no docs and no docs folder and mocked discourse
    act: when _run_reconcile is called
    assert: Nothing is done, and empty result is return with a warning.
    """
    user_inputs = factories.UserInputsFactory(dry_run=False, delete_pages=True)

    with caplog.at_level(logging.WARNING):
        output = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    assert not output
    assert len(caplog.records) == 1
    assert "Cannot run any reconcile to Discourse" in caplog.records[0].message
    assert "not any docs folder" in caplog.records[0].message


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
def test__run_reconcile_on_tag_commit(caplog, mocked_clients):
    """
    arrange: given metadata with name and docs and docs folder and mocked discourse and repository
        at the same commit as the documentation tag
    act: when _run_reconcile is called
    assert: Nothing is done, and empty result is return with an info.
    """
    repository_client = mocked_clients.repository

    (docs_folder := repository_client.base_path / "docs").mkdir()
    (docs_folder / "index.md").write_text("index content")
    (docs_folder / "page.md").write_text("page content 2")

    repository_client.switch("main").update_branch("First commit of documentation")

    repository_client._git_repo.git.tag("-f", DOCUMENTATION_TAG)
    user_inputs = factories.UserInputsFactory(commit_sha=repository_client.current_commit)

    with caplog.at_level(logging.WARNING):
        output = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    assert not output
    assert len(caplog.records) == 1
    assert "Cannot run any reconcile to Discourse" in caplog.records[0].message
    assert "same commit" in caplog.records[0].message


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
def test__run_migrate_server_error_index(repository_client: pull_request.RepositoryClient):
    """
    arrange: given metadata with name and docs but no docs directory and mocked discourse
        that raises an exception during index file fetching
    act: when _run_migrate is called
    assert: Server error is raised with page retrieval fail.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = exceptions.DiscourseError
    user_inputs = factories.UserInputsFactory()

    repository_client.switch("main")._git_repo.git.tag("-f", DOCUMENTATION_TAG)

    with pytest.raises(exceptions.ServerError) as exc:
        run_migrate(
            clients=Clients(discourse=mocked_discourse, repository=repository_client),
            user_inputs=user_inputs,
        )

    assert "Index page retrieval failed" == str(exc.value)


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
def test__run_migrate_server_error_topic(mocked_clients):
    """
    arrange: given metadata with name and docs but no docs directory and mocked discourse
        that raises an exception during topic retrieval
    act: when _run_migrate is called
    assert: MigrationError is raised.
    """
    user_inputs = factories.UserInputsFactory()
    index_content = """Content Title

    Content description.

    # Navigation

    | Level | Path | Navlink |
    | -- | -- | -- |
    | 1 | path-1 | [Link](/t/link-to-1) |
    """
    mocked_clients.discourse.retrieve_topic.side_effect = [
        index_content,
        exceptions.DiscourseError,
    ]

    mocked_clients.repository.switch("main")._git_repo.git.tag("-f", DOCUMENTATION_TAG)

    with pytest.raises(exceptions.MigrationError):
        run_migrate(
            clients=mocked_clients,
            user_inputs=user_inputs,
        )


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_migrate_no_docs_information(caplog, mocked_clients):
    """
    arrange: given metadata with name and docs but no docs directory and mocked discourse
        that raises an exception during topic retrieval
    act: when _run_migrate is called
    assert: MigrationError is raised.
    """
    user_inputs = factories.UserInputsFactory()

    mocked_clients.repository.switch("main")._git_repo.git.tag("-f", DOCUMENTATION_TAG)

    with caplog.at_level(logging.INFO):
        # run is repeated in unit tests / integration tests
        returned_migration_reports = run_migrate(
            clients=mocked_clients, user_inputs=user_inputs
        )  # pylint: disable=duplicate-code

    assert not returned_migration_reports
    assert len(caplog.records) == 1
    assert "Cannot run any migration from Discourse" in caplog.records[0].message


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
def test__run_migrate(
    mocked_clients,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    mock_pull_request: PullRequest,
):
    """
    arrange: given metadata with name and docs but no docs directory and mocked discourse
    act: when _run_migrate is called
    assert: docs are migrated and a report on migrated documents are returned.
    """
    index_content = """Content header.

    Content body."""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | path-1 | [Tutorials](link-1) |"""
    index_page = f"{index_content}{index_table}"

    mocked_clients.discourse.retrieve_topic.side_effect = [
        index_page,
        (link_content := "link 1 content"),
    ]

    user_inputs = factories.UserInputsFactory()

    mocked_clients.repository.switch("main")._git_repo.git.tag("-f", DOCUMENTATION_TAG)

    returned_migration_reports = run_migrate(
        clients=mocked_clients,
        user_inputs=user_inputs,
    )

    upstream_git_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert returned_migration_reports == {mock_pull_request.html_url: types_.ActionResult.SUCCESS}
    assert (
        index_file := upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "index.md"
    ).is_file()
    assert (
        path_file := upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "path-1.md"
    ).is_file()
    assert index_file.read_text(encoding="utf-8") == index_page
    assert path_file.read_text(encoding="utf-8") == link_content


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
@mock.patch("src.repository.Client.get_pull_request", return_value="test_url")
def test__run_migrate_with_pull_request(
    _,
    mocked_clients,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    mock_pull_request: PullRequest,
):
    """
    arrange: given metadata with name and docs and docs directory with updated content
        and pull request already open and mocked discourse
    act: when _run_migrate is called
    assert: docs are migrated and the remote branch is updated.
    """
    # mock_get_pull.return_value = "test-url"

    index_content = """Content header.

    Content body.\n"""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | path-1 | [empty-navlink]() |
    | 2 | file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, f"{navlink_page} new"]

    # Set up remote repository with content
    (docs_folder := upstream_repository_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_page)
    (docs_folder / "path-1").mkdir()
    (docs_folder / "path-1" / "file-1.md").write_text(navlink_page)

    # commit data to upstream
    head = upstream_git_repo.create_head(pull_request.DEFAULT_BRANCH_NAME)
    head.checkout()

    upstream_git_repo.git.add(".")
    upstream_git_repo.git.commit("-m", "first commit of documentation")
    upstream_git_repo.git.checkout(BASE_REMOTE_BRANCH)

    user_inputs = factories.UserInputsFactory()

    mocked_clients.repository.switch("main")._git_repo.git.tag("-f", DOCUMENTATION_TAG)

    returned_migration_reports = run_migrate(
        clients=mocked_clients,
        user_inputs=user_inputs,
    )

    assert returned_migration_reports == {mock_pull_request.html_url: types_.ActionResult.SUCCESS}

    upstream_git_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)

    assert "first commit of documentation" not in upstream_git_repo.head.commit.message
    assert (
        upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "path-1" / "file-1.md"
    ).read_text() == f"{navlink_page} new"


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
@mock.patch("src.repository.Client.get_pull_request", return_value="test_url")
def test__run_migrate_with_pull_request_no_modification(
    _,
    mocked_clients,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    mock_pull_request: PullRequest,
):
    """
    arrange: given metadata with name and docs and docs directory with same content
        and pull request already open and mocked discourse
    act: when _run_migrate is called
    assert: docs are migrated and the remote branch is left intact.
    """
    # mock_get_pull.return_value = "test-url"

    index_content = """Content header.

    Content body.\n"""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | path-1 | [empty-navlink]() |
    | 2 | file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]

    # Set up remote repository with content
    (docs_folder := upstream_repository_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_page)
    (docs_folder / "path-1").mkdir()
    (docs_folder / "path-1" / "file-1.md").write_text(navlink_page)

    # commit data to upstream
    head = upstream_git_repo.create_head(pull_request.DEFAULT_BRANCH_NAME)
    head.checkout()

    upstream_git_repo.git.add(".")
    upstream_git_repo.git.commit("-m", "first commit of documentation")
    _hash = upstream_git_repo.head.ref.commit.hexsha
    upstream_git_repo.git.checkout(BASE_REMOTE_BRANCH)

    user_inputs = factories.UserInputsFactory()

    mocked_clients.repository.switch("main")._git_repo.git.tag("-f", DOCUMENTATION_TAG)

    returned_migration_reports = run_migrate(
        clients=mocked_clients,
        user_inputs=user_inputs,
    )

    assert returned_migration_reports == {mock_pull_request.html_url: types_.ActionResult.SUCCESS}

    upstream_git_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)

    assert "first commit of documentation" in upstream_git_repo.head.commit.message
    assert upstream_git_repo.head.ref.commit.hexsha == _hash


@pytest.mark.usefixtures("patch_create_repository_client")
def test_run_no_docs_empty_dir(mocked_clients):
    """
    arrange: given a path with a metadata.yaml that has no docs key and has empty docs directory
        and mocked discourse
    act: when run is called
    assert: then an index page is created with empty navigation table.
    """
    repository_path = mocked_clients.repository.base_path

    create_metadata_yaml(content=f"{METADATA_NAME_KEY}: name 1", path=repository_path)
    (repository_path / DOCUMENTATION_FOLDER_NAME).mkdir()
    mocked_clients.discourse.create_topic.return_value = (url := "url 1")
    user_inputs = factories.UserInputsFactory()

    # run is repeated in unit tests / integration tests
    returned_page_interactions = run_reconcile(
        clients=mocked_clients, user_inputs=user_inputs
    )  # pylint: disable=duplicate-code

    mocked_clients.discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{constants.NAVIGATION_TABLE_START.strip()}",
    )
    assert returned_page_interactions == {url: types_.ActionResult.SUCCESS}


@pytest.mark.usefixtures("patch_create_repository_client")
def test_run_no_docs_dir(
    mocked_clients,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    mock_pull_request: PullRequest,
):
    """
    arrange: given a path with a metadata.yaml that has docs key and no docs directory
        and mocked discourse
    act: when run is called
    assert: then docs from the server is migrated into local docs path and the files created
        are return as the result.
    """
    repository_path = mocked_clients.repository.base_path

    create_metadata_yaml(
        content=f"{METADATA_NAME_KEY}: name 1\n" f"{METADATA_DOCS_KEY}: docsUrl",
        path=repository_path,
    )
    index_content = """Content header.

    Content body.\n"""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | path-1 | [empty-navlink]() |
    | 2 | file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]
    user_inputs = factories.UserInputsFactory()

    mocked_clients.repository.switch("main")._git_repo.git.tag("-f", DOCUMENTATION_TAG)

    # run is repeated in unit tests / integration tests
    returned_migration_reports = run_migrate(
        clients=mocked_clients, user_inputs=user_inputs
    )  # pylint: disable=duplicate-code

    upstream_git_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert returned_migration_reports == {mock_pull_request.html_url: types_.ActionResult.SUCCESS}
    assert (
        index_file := upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "index.md"
    ).is_file()
    assert (
        path_file := upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "path-1" / "file-1.md"
    ).is_file()
    assert index_file.read_text(encoding="utf-8") == index_page
    assert path_file.read_text(encoding="utf-8") == navlink_page


def test_run_migrate_same_content_local_and_server(caplog, mocked_clients):
    """
    arrange: given a path with a metadata.yaml that has docs key and docs directory aligned
        and mocked discourse (with tag and main branch aligned)
    act: when run_migrate is called
    assert: then nothing is done as the two versions are the compatible.
    """
    repository_path = mocked_clients.repository.base_path

    create_metadata_yaml(
        content=f"{METADATA_NAME_KEY}: name 1\n" f"{METADATA_DOCS_KEY}: https://discourse/t/docs",
        path=repository_path,
    )
    index_content = """Content header.

    Content body.\n"""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | path-1 | [empty-navlink]() |
    | 2 | file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]

    (docs_folder := mocked_clients.repository.base_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_page)
    (docs_folder / "path-1").mkdir()
    (docs_folder / "path-1" / "file-1.md").write_text(navlink_page)

    mocked_clients.repository.switch("main").update_branch("First document version")

    user_inputs = factories.UserInputsFactory()
    mocked_clients.repository._git_repo.git.tag("-f", DOCUMENTATION_TAG)

    with caplog.at_level(logging.INFO):
        # run is repeated in unit tests / integration tests
        returned_migration_reports = run_migrate(
            clients=mocked_clients, user_inputs=user_inputs
        )  # pylint: disable=duplicate-code

    assert not returned_migration_reports
    assert any("No community contribution found" in record.message for record in caplog.records)
