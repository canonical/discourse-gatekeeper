# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=too-many-lines
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
    pre_flight_checks,
    run_migrate,
    run_reconcile,
    types_,
)
from src.clients import get_clients
from src.constants import DEFAULT_BRANCH
from src.metadata import METADATA_DOCS_KEY, METADATA_NAME_KEY
from src.repository import DEFAULT_BRANCH_NAME
from src.repository import Client as RepositoryClient

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

    with mocked_clients.repository.with_branch(DEFAULT_BRANCH) as repo:
        (repo.base_path / DOCUMENTATION_FOLDER_NAME).mkdir()
        (repo.base_path / "placeholder-file.md").touch()
        repo.update_branch("new commit", directory=None)
        user_inputs = factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repo.current_commit
        )

        returned_page_interactions = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    mocked_clients.discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{constants.NAVIGATION_TABLE_START.strip()}",
    )
    assert returned_page_interactions is not None
    assert returned_page_interactions.topics == {url: types_.ActionResult.SUCCESS}


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_empty_local_server_from_non_base_branch(mocked_clients):
    """
    arrange: given metadata with name but not docs and empty docs folder and mocked discourse
    act: when _run_reconcile is called in non dry-run mode and from a branch other than the
            base branch
    assert: then an error is thrown when tagging the branch
    """
    mocked_clients.discourse.create_topic.return_value = "url 1"

    branch = "fake-branch"

    with mocked_clients.repository.create_branch(branch, DEFAULT_BRANCH).with_branch(
        branch
    ) as repo:
        (repo.base_path / DOCUMENTATION_FOLDER_NAME).mkdir()
        (repo.base_path / "placeholder-file.md").touch()
        repo.update_branch("new commit", directory=None)
        user_inputs = factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repo.current_commit
        )

        with pytest.raises(exceptions.TaggingNotAllowedError) as exc_info:
            run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

        assert_substrings_in_string(
            (repo.current_commit, f"outside of {DEFAULT_BRANCH}"), str(exc_info.value)
        )


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

    mocked_clients.discourse.create_topic.side_effect = [
        (page_url := "url 1"),
        (index_url := "url 2"),
    ]

    with mocked_clients.repository.with_branch(DEFAULT_BRANCH) as repo:
        (docs_folder := repo.base_path / "docs").mkdir()
        (docs_folder / "index.md").write_text(index_content := "index content")
        (docs_folder / "page.md").write_text(page_content := "page content")
        repo.update_branch("new commit")

        user_inputs = factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repo.current_commit
        )

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
    assert returned_page_interactions is not None
    assert returned_page_interactions.topics == {
        page_url: types_.ActionResult.SUCCESS,
        index_url: types_.ActionResult.SUCCESS,
    }


@mock.patch("src.repository.Client.get_file_content_from_tag")
@pytest.mark.parametrize(
    "branch_name",
    [pytest.param(DEFAULT_BRANCH), pytest.param("other-main")],
)
def test_run_reconcile_same_content_local_and_server(
    get_file_content_from_tag,
    caplog,
    mocked_clients,
    branch_name,
):
    """
    arrange: given a path with a metadata.yaml that has docs key and docs directory aligned
        and mocked discourse (with tag and branch aligned)
    act: when run_reconcile is called
    assert: that nothing is done, and, depending on the branch we are at, the DOCUMENTATION_TAG
        is updated with the current commit if we are in the base branch
    """
    repository_path = mocked_clients.repository.base_path

    if branch_name != DEFAULT_BRANCH:
        mocked_clients.repository.create_branch(branch_name, DEFAULT_BRANCH)

    create_metadata_yaml(
        content=f"{METADATA_NAME_KEY}: name 1\n" f"{METADATA_DOCS_KEY}: https://discourse/t/docs",
        path=repository_path,
    )
    index_content = """Content header lorem.

    Content body."""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | folder | [Folder]() |
    | 2 | their-file-1 | [file-navlink-title](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "# file-navlink-title\nfile-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]

    (docs_folder := mocked_clients.repository.base_path / "docs").mkdir()
    (index_file := docs_folder / "index.md").write_text(index_content)
    (docs_folder / "folder").mkdir()
    (their_file := docs_folder / "folder" / "their-file-1.md").write_text(navlink_page)

    mocked_clients.repository.switch(DEFAULT_BRANCH).update_branch(
        "First document version", directory=None
    )

    def patch(path, tag_name) -> str:
        """Return the patches content of a given tag.

        Args:
            path: path of the file
            tag_name: name of the tag

        Returns:
            Content of the given tag
        """
        assert tag_name

        if path == str(index_file.relative_to(repository_path)):
            return index_content
        if path == str(their_file.relative_to(repository_path)):
            return navlink_page
        return ""

    get_file_content_from_tag.side_effect = patch

    mocked_clients.repository.tag_commit(
        DOCUMENTATION_TAG, mocked_clients.repository.current_commit
    )

    (mocked_clients.repository.base_path / "placeholder.md").touch()

    mocked_clients.repository.switch(DEFAULT_BRANCH).update_branch(
        "Placeholder modification outside of docs", directory=None
    )

    user_inputs = factories.UserInputsFactory(
        commit_sha=mocked_clients.repository.current_commit, base_branch=branch_name
    )

    assert (
        mocked_clients.repository.tag_exists(DOCUMENTATION_TAG)
        != mocked_clients.repository.current_commit
    )

    caplog.clear()
    with caplog.at_level(logging.INFO):
        # run is repeated in unit tests / integration tests
        returned_reconcile_reports = run_reconcile(
            clients=mocked_clients, user_inputs=user_inputs
        )  # pylint: disable=duplicate-code

    assert returned_reconcile_reports

    assert "Reconcile not required to run" in caplog.text

    if branch_name == DEFAULT_BRANCH:
        assert "Updating the tag" in caplog.text
        assert (
            mocked_clients.repository.tag_exists(DOCUMENTATION_TAG)
            == mocked_clients.repository.current_commit
        )
    else:
        # Running outside of base branch
        assert (
            mocked_clients.repository.tag_exists(DOCUMENTATION_TAG)
            != mocked_clients.repository.current_commit
        )


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_local_contents_index(mocked_clients):
    """
    arrange: given metadata with name but not docs and docs folder with multiple files, contents
        index with the files and mocked discourse
    act: when _run_reconcile is called
    assert: then a documentation page is created and an index page is created with a navigation
        page with a reference to the documentation pages based on the order in the contents index.
    """
    mocked_clients.discourse.create_topic.side_effect = [
        (page_2_url := "url 2"),
        (page_1_url := "url 1"),
        (index_url := "url 3"),
    ]

    with mocked_clients.repository.with_branch(DEFAULT_BRANCH) as repo:
        (docs_dir := repo.base_path / "docs").mkdir()
        (docs_dir / (page_1 := Path("page_1.md"))).write_text("page 1 content", encoding="utf-8")
        (docs_dir / (page_2 := Path("page_2.md"))).write_text("page 2 content", encoding="utf-8")
        (docs_dir / "index.md").write_text(
            f"""{(index_content := 'index content')}
# contents
- [{(page_2_title := "Page 2")}]({page_2})
- [{(page_1_title := "Page 1")}]({page_1})
""",
            encoding="utf-8",
        )
        repo.update_branch("new commit")

        user_inputs = factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repo.current_commit
        )

        returned_page_interactions = run_reconcile(
            clients=mocked_clients,
            user_inputs=user_inputs,
        )

    assert mocked_clients.discourse.create_topic.call_count == 3
    mocked_clients.discourse.create_topic.assert_any_call(
        title="Name 1 Documentation Overview",
        content=(
            f"{index_content}{constants.NAVIGATION_TABLE_START}\n"
            f"| 1 | page-2 | [{page_2_title}]({page_2_url}) |\n"
            f"| 1 | page-1 | [{page_1_title}]({page_1_url}) |"
        ),
    )
    assert returned_page_interactions is not None
    assert returned_page_interactions.topics == {
        page_2_url: types_.ActionResult.SUCCESS,
        page_1_url: types_.ActionResult.SUCCESS,
        index_url: types_.ActionResult.SUCCESS,
    }


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_hidden_item(mocked_clients):
    """
    arrange: given metadata with name but not docs and docs folder with single commented out file
        and mocked discourse
    act: when _run_reconcile is called
    assert: then a documentation page is created and an index page is created with a navigation
        page without a level for the commented out item.
    """
    mocked_clients.discourse.create_topic.side_effect = [
        (page_1_url := "url 1"),
        (index_url := "url 3"),
    ]

    with mocked_clients.repository.with_branch(DEFAULT_BRANCH) as repo:
        (docs_dir := repo.base_path / "docs").mkdir()
        (docs_dir / (page_1 := Path("page_1.md"))).write_text("page 1 content", encoding="utf-8")
        (docs_dir / "index.md").write_text(
            f"""{(index_content := 'index content')}
# contents
<!-- - [{(page_1_title := "Page 1")}]({page_1}) -->
""",
            encoding="utf-8",
        )
        repo.update_branch("new commit")

        user_inputs = factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repo.current_commit
        )

        returned_page_interactions = run_reconcile(
            clients=mocked_clients,
            user_inputs=user_inputs,
        )

    assert mocked_clients.discourse.create_topic.call_count == 2
    mocked_clients.discourse.create_topic.assert_any_call(
        title="Name 1 Documentation Overview",
        content=(
            f"{index_content}{constants.NAVIGATION_TABLE_START}\n"
            f"| | page-1 | [{page_1_title}]({page_1_url}) |"
        ),
    )
    assert returned_page_interactions is not None
    assert returned_page_interactions.topics == {
        page_1_url: types_.ActionResult.SUCCESS,
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
    assert returned_page_interactions is not None
    assert not returned_page_interactions.topics


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs=None),
)
def test__run_reconcile_local_empty_server_dry_run_no_tag(mocked_clients, upstream_git_repo):
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
    upstream_git_repo.git.tag("-d", DOCUMENTATION_TAG)

    returned_page_interactions = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    mocked_clients.discourse.create_topic.assert_not_called()
    assert returned_page_interactions is not None
    assert not returned_page_interactions.topics


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

    with mocked_clients.repository.with_branch(DEFAULT_BRANCH) as repo:
        (repo.base_path / "docs").mkdir()
        (repo.base_path / "placeholder.md").touch()
        repo.update_branch("new commit", directory=None)

        user_inputs = factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repo.current_commit
        )

        returned_page_interactions = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    mocked_clients.discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{constants.NAVIGATION_TABLE_START.strip()}",
    )
    assert returned_page_interactions is not None
    assert not returned_page_interactions.topics


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

    caplog.clear()
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

    repository_client.switch(DEFAULT_BRANCH).update_branch("First commit of documentation")

    repository_client.tag_commit(DOCUMENTATION_TAG, repository_client.current_commit)
    user_inputs = factories.UserInputsFactory(commit_sha=repository_client.current_commit)

    caplog.clear()
    with caplog.at_level(level=logging.WARNING):
        output = run_reconcile(clients=mocked_clients, user_inputs=user_inputs)

    assert not output
    assert len(caplog.records) == 1
    assert "Cannot run any reconcile to Discourse" in caplog.records[0].message
    assert "same commit" in caplog.records[0].message


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
def test__run_migrate_server_error_index(repository_client: RepositoryClient):
    """
    arrange: given metadata with name and docs but no docs directory and mocked discourse
        that raises an exception during index file fetching
    act: when _run_migrate is called
    assert: Server error is raised with page retrieval fail.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.retrieve_topic.side_effect = exceptions.DiscourseError
    user_inputs = factories.UserInputsFactory()

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
    arrange: given metadata with name but no docs directory and information in metadata
    act: when _run_migrate is called
    assert: Nothing is done and logs are outputted to notify that no migration was run
    """
    user_inputs = factories.UserInputsFactory()

    caplog.clear()
    with caplog.at_level(logging.INFO):
        # run is repeated in unit tests / integration tests
        returned_migration_reports = run_migrate(
            clients=mocked_clients, user_inputs=user_inputs
        )  # pylint: disable=duplicate-code

    assert not returned_migration_reports
    assert len(caplog.records) == 1
    assert "Cannot run migration from Discourse" in caplog.records[0].message


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

    returned_migration_reports = run_migrate(
        clients=mocked_clients,
        user_inputs=user_inputs,
    )

    upstream_git_repo.git.checkout(DEFAULT_BRANCH_NAME)
    assert returned_migration_reports is not None
    assert returned_migration_reports.pull_request_url == mock_pull_request.html_url
    assert returned_migration_reports.action == types_.PullRequestAction.OPENED
    assert (
        index_file := upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "index.md"
    ).is_file()
    assert (
        path_file := upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "path-1.md"
    ).is_file()
    assert index_file.read_text(encoding="utf-8") == index_content
    assert path_file.read_text(encoding="utf-8") == link_content


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
@mock.patch("src.repository.Client.get_pull_request")
def test__run_migrate_with_pull_request(
    mock_get_pull_request,
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
    mock_get_pull_request.return_value = mock_pull_request

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
    head = upstream_git_repo.create_head(DEFAULT_BRANCH_NAME)
    head.checkout()

    upstream_git_repo.git.add(".")
    upstream_git_repo.git.commit("-m", "first commit of documentation")
    upstream_git_repo.git.checkout(BASE_REMOTE_BRANCH)

    user_inputs = factories.UserInputsFactory()

    returned_migration_reports = run_migrate(
        clients=mocked_clients,
        user_inputs=user_inputs,
    )

    assert returned_migration_reports is not None
    assert returned_migration_reports.pull_request_url == mock_pull_request.html_url
    assert returned_migration_reports.action == types_.PullRequestAction.UPDATED

    upstream_git_repo.git.checkout(DEFAULT_BRANCH_NAME)

    assert "first commit of documentation" not in upstream_git_repo.head.commit.message
    assert (
        upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "path-1" / "file-1.md"
    ).read_text() == f"{navlink_page} new"


@mock.patch(
    "src.repository.Client.metadata",
    types_.Metadata(name="name 1", docs="http://discourse/t/docs"),
)
@mock.patch("src.repository.Client.get_pull_request")
def test__run_migrate_with_pull_request_no_modification(
    mock_get_pull_request,
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
    mock_get_pull_request.return_value = mock_pull_request

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
    (docs_folder / "index.md").write_text(index_content)
    (docs_folder / "path-1").mkdir()
    (docs_folder / "path-1" / "file-1.md").write_text(navlink_page)

    # commit data to upstream
    head = upstream_git_repo.create_head(DEFAULT_BRANCH_NAME)
    head.checkout()

    upstream_git_repo.git.add(".")
    upstream_git_repo.git.commit("-m", "first commit of documentation")
    _hash = upstream_git_repo.head.ref.commit.hexsha
    upstream_git_repo.git.checkout(BASE_REMOTE_BRANCH)

    user_inputs = factories.UserInputsFactory()

    returned_migration_reports = run_migrate(
        clients=mocked_clients,
        user_inputs=user_inputs,
    )

    assert returned_migration_reports is not None
    assert returned_migration_reports.pull_request_url == mock_pull_request.html_url
    assert returned_migration_reports.action == types_.PullRequestAction.UPDATED

    upstream_git_repo.git.checkout(DEFAULT_BRANCH_NAME)

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
    mocked_clients.discourse.create_topic.return_value = (url := "url 1")

    with mocked_clients.repository.with_branch(DEFAULT_BRANCH) as repo:
        (repository_path / DOCUMENTATION_FOLDER_NAME).mkdir()
        create_metadata_yaml(content=f"{METADATA_NAME_KEY}: name 1", path=repository_path)
        (repository_path / "placeholder-file.md").touch()
        repo.update_branch("new commit", directory=None)
        user_inputs = factories.UserInputsFactory(commit_sha=repo.current_commit)

        # run is repeated in unit tests / integration tests
        returned_page_interactions = run_reconcile(
            clients=mocked_clients, user_inputs=user_inputs
        )  # pylint: disable=duplicate-code

    mocked_clients.discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{constants.NAVIGATION_TABLE_START.strip()}",
    )
    assert returned_page_interactions is not None
    assert returned_page_interactions.topics == {url: types_.ActionResult.SUCCESS}


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
    index_content = """Content header in here.

    Content body.\n"""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | my-path-1 | [empty-navlink]() |
    | 2 | my-file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]
    user_inputs = factories.UserInputsFactory()

    # run is repeated in unit tests / integration tests
    returned_migration_reports = run_migrate(
        clients=mocked_clients, user_inputs=user_inputs
    )  # pylint: disable=duplicate-code

    upstream_git_repo.git.checkout(DEFAULT_BRANCH_NAME)
    assert returned_migration_reports is not None
    assert returned_migration_reports.pull_request_url == mock_pull_request.html_url
    assert returned_migration_reports.action == types_.PullRequestAction.OPENED
    assert (
        index_file := upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "index.md"
    ).is_file()
    assert (
        path_file := upstream_repository_path
        / DOCUMENTATION_FOLDER_NAME
        / "my-path-1"
        / "my-file-1.md"
    ).is_file()
    assert index_file.read_text(encoding="utf-8") == index_content
    assert path_file.read_text(encoding="utf-8") == navlink_page


@pytest.mark.usefixtures("patch_create_repository_client")
def test_run_no_docs_dir_no_tag(
    mocked_clients,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    mock_pull_request: PullRequest,
):
    """
    arrange: given a path with a metadata.yaml that has docs key and no docs directory
        and mocked discourse and repository has not tag
    act: when run is called
    assert: then docs from the server is migrated into local docs path and the files created
        are return as the result.
    """
    mocked_clients.repository._git_repo.git.tag("-d", DOCUMENTATION_TAG)
    upstream_git_repo.git.tag("-d", DOCUMENTATION_TAG)

    repository_path = mocked_clients.repository.base_path

    create_metadata_yaml(
        content=f"{METADATA_NAME_KEY}: name 1\n" f"{METADATA_DOCS_KEY}: docsUrl",
        path=repository_path,
    )
    index_content = """Content header 2.

    Content body.\n"""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | t-path-1 | [empty-navlink]() |
    | 2 | t-file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]
    user_inputs = factories.UserInputsFactory()

    # run is repeated in unit tests / integration tests
    returned_migration_reports = run_migrate(
        clients=mocked_clients, user_inputs=user_inputs
    )  # pylint: disable=duplicate-code

    upstream_git_repo.git.checkout(DEFAULT_BRANCH_NAME)
    assert returned_migration_reports is not None
    assert returned_migration_reports.pull_request_url == mock_pull_request.html_url
    assert returned_migration_reports.action == types_.PullRequestAction.OPENED
    assert (
        index_file := upstream_repository_path / DOCUMENTATION_FOLDER_NAME / "index.md"
    ).is_file()
    assert (
        path_file := upstream_repository_path
        / DOCUMENTATION_FOLDER_NAME
        / "t-path-1"
        / "t-file-1.md"
    ).is_file()
    assert index_file.read_text(encoding="utf-8") == index_content
    assert path_file.read_text(encoding="utf-8") == navlink_page


@mock.patch("github.PullRequest.PullRequest")
def test_run_migrate_same_content_local_and_server(mock_edit_pull_request, caplog, mocked_clients):
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
    index_content = """Content header lorem.

    Content body."""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | their-path-1 | [empty-navlink]() |
    | 2 | their-file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]

    (docs_folder := mocked_clients.repository.base_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_content)
    (docs_folder / "their-path-1").mkdir()
    (docs_folder / "their-path-1" / "their-file-1.md").write_text(navlink_page)

    mocked_clients.repository.switch(DEFAULT_BRANCH).update_branch(
        "First document version", directory=None
    )

    user_inputs = factories.UserInputsFactory()
    mocked_clients.repository.tag_commit(
        DOCUMENTATION_TAG, mocked_clients.repository.current_commit
    )

    caplog.clear()
    with caplog.at_level(logging.INFO):
        # run is repeated in unit tests / integration tests
        returned_migration_reports = run_migrate(
            clients=mocked_clients, user_inputs=user_inputs
        )  # pylint: disable=duplicate-code

    assert not returned_migration_reports
    assert any("No community contribution found" in record.message for record in caplog.records)
    edit_call_args = [
        kwargs for name, args, kwargs in mock_edit_pull_request.mock_calls if name.endswith("edit")
    ]
    assert not edit_call_args


@mock.patch("src.repository.Client.get_pull_request")
@mock.patch("github.PullRequest.PullRequest")
def test_run_migrate_same_content_local_and_server_open_pr(
    mocked_get_pull_request, mock_edit_pull_request, caplog, mocked_clients, mock_pull_request
):
    """
    arrange: given a path with a metadata.yaml that has docs key and docs directory aligned
        and mocked discourse (with tag and main branch aligned) and there is an open PR
    act: when run_migrate is called
    assert: then nothing is done as the two versions are the compatible and the PR is closed.
    """
    mocked_get_pull_request.return_value = mock_pull_request

    repository_path = mocked_clients.repository.base_path

    create_metadata_yaml(
        content=f"{METADATA_NAME_KEY}: name 1\n" f"{METADATA_DOCS_KEY}: https://discourse/t/docs",
        path=repository_path,
    )
    index_content = """Content header lorem.

    Content body.\n"""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | their-path-1 | [empty-navlink]() |
    | 2 | their-file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]

    (docs_folder := mocked_clients.repository.base_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_content)
    (docs_folder / "their-path-1").mkdir()
    (docs_folder / "their-path-1" / "their-file-1.md").write_text(navlink_page)

    mocked_clients.repository.switch(DEFAULT_BRANCH).update_branch(
        "First document version", directory=None
    )

    user_inputs = factories.UserInputsFactory()
    mocked_clients.repository.tag_commit(
        DOCUMENTATION_TAG, mocked_clients.repository.current_commit
    )

    caplog.clear()
    with caplog.at_level(logging.INFO):
        # run is repeated in unit tests / integration tests
        returned_migration_reports = run_migrate(
            clients=mocked_clients, user_inputs=user_inputs
        )  # pylint: disable=duplicate-code

    assert returned_migration_reports
    assert returned_migration_reports.action == types_.PullRequestAction.CLOSED
    assert any("No community contribution found" in record.message for record in caplog.records)
    edit_call_args = [
        kwargs for name, args, kwargs in mock_edit_pull_request.mock_calls if name.endswith("edit")
    ]
    assert len(edit_call_args) == 1
    assert edit_call_args[0] == {"state": "closed"}


def test_pre_flight_checks_ok(mocked_clients):
    """
    arrange: given a repository in a consistent state, meaning that the documentation tag is
        part of the base_branch
    act: when pre_flight_checks is called
    assert: then the function returns True.
    """
    user_inputs = factories.UserInputsFactory()

    assert pre_flight_checks(mocked_clients, user_inputs)


def test_pre_flight_checks_ok_tag_not_exists(mocked_clients, upstream_git_repo):
    """
    arrange: given a repository in a consistent state with no documentation tag
    act: when pre_flight_checks is called
    assert: then the function returns True and a documentation tag is created.
    """
    mocked_clients.repository._git_repo.git.tag("-d", DOCUMENTATION_TAG)
    upstream_git_repo.git.tag("-d", DOCUMENTATION_TAG)

    user_inputs = factories.UserInputsFactory()

    assert pre_flight_checks(mocked_clients, user_inputs)
    assert mocked_clients.repository.tag_exists(DOCUMENTATION_TAG)


def test_pre_flight_checks_fail(mocked_clients):
    """
    arrange: given a repository in an inconsistent state, meaning that the documentation tag is
        not part of the base_branch
    act: when pre_flight_checks is called
    assert: then the function returns False.
    """
    user_inputs = factories.UserInputsFactory()

    repository_path = mocked_clients.repository.base_path

    with mocked_clients.repository.create_branch("fake-branch").with_branch("fake-branch") as repo:
        (repository_path / "placeholder.md").touch()
        repo.update_branch("New commit in fake-branch", directory=None)
        repo.tag_commit(DOCUMENTATION_TAG, repo.current_commit)

    (repository_path / "placeholder-2.md").touch()
    mocked_clients.repository.update_branch("New commit in main", directory=None)

    assert not pre_flight_checks(mocked_clients, user_inputs)
