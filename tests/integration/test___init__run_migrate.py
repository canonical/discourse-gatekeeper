# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for running the migrate action."""

# This test is fairly complex as it simulates sequential action runs
# pylint: disable=too-many-arguments,too-many-locals,too-many-statements

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from git.repo import Repo
from github.PullRequest import PullRequest

from src import Clients, constants, metadata, migration, run_migrate
from src.constants import DEFAULT_BRANCH, DOCUMENTATION_TAG
from src.discourse import Discourse
from src.repository import DEFAULT_BRANCH_NAME
from src.repository import Client as RepositoryClient
from src.types_ import ActionResult, PullRequestAction

from .. import factories
from ..conftest import BASE_REMOTE_BRANCH
from ..unit.helpers import assert_substrings_in_string, create_metadata_yaml

pytestmark = pytest.mark.migrate


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_create_repository_client")
async def test_run_migrate(
    discourse_address: str,
    discourse_api: Discourse,
    caplog: pytest.LogCaptureFixture,
    repository_path: Path,
    upstream_git_repo: Repo,
    upstream_repository_path: Path,
    mock_pull_request: PullRequest,
    mock_github_repo: MagicMock,
    monkeypatch,
):
    """
    arrange: given running discourse server
    act: when run is called with:
        1. with no docs dir and no custom branchname provided
        2. with no docs dir and custom branchname provided
        3. with modification to an existing open PR
        4. After merging the PR, content is in sync with Discourse
    assert: then:
        1. the documentation files are pushed to default branch
        2. the documentation files are pushed to custom branch
        3. a new commit is added to the PR
        4. no operation are done
    """
    caplog.set_level(logging.INFO)
    document_name = "migration name 1"
    discourse_prefix = discourse_address
    content_page_1 = factories.ContentPageFactory()
    content_page_1_url = discourse_api.create_topic(
        title=content_page_1.title,
        content=content_page_1.content,
    ).removeprefix(discourse_prefix)
    content_page_2 = factories.ContentPageFactory()
    content_page_2_url = discourse_api.create_topic(
        title=content_page_2.title,
        content=content_page_2.content,
    ).removeprefix(discourse_prefix)
    content_page_3 = factories.ContentPageFactory()
    content_page_3_url = discourse_api.create_topic(
        title=content_page_3.title,
        content=content_page_3.content,
    ).removeprefix(discourse_prefix)
    content_page_4 = factories.ContentPageFactory()
    content_page_4_url = discourse_api.create_topic(
        title=content_page_4.title,
        content=content_page_4.content,
    ).removeprefix(discourse_prefix)
    index_page_content = f"""Testing index page.

    Testing index page content.

    # Navigation

    | Level | Path | Navlink |
    | -- | -- | -- |
    | 1 | group-1 | [Group 1]() |
    | 1 | group-2 | [Group 2]() |
    | 2 | group-2-content-1 | [{content_page_1.content}]({content_page_1_url}) |
    | 2 | group-2-content-2 | [{content_page_2.content}]({content_page_2_url}) |
    | 1 | group-3 | [Group 3]() |
    | 2 | group-3-group-4 | [Group 4]() |
    | 3 | group-3-group-4-content-3 | [{content_page_3.content}]({content_page_3_url}) |
    | 2 | group-3-content-4 | [{content_page_4.content}]({content_page_4_url}) |
    | 1 | group-5 | [Group 5]() |"""
    index_url = discourse_api.create_topic(
        title=f"{document_name.replace('-', ' ').title()} Documentation Overview",
        content=index_page_content,
    )

    repository_client = RepositoryClient(Repo(repository_path), mock_github_repo)

    # 1. with no docs dir and a metadata.yaml with docs key
    caplog.clear()

    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: name 1\n{metadata.METADATA_DOCS_KEY}: {index_url}",
        path=repository_path,
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "first commit of metadata", directory=None
    )
    repository_client.tag_commit(DOCUMENTATION_TAG, repository_client.current_commit)

    output_migrate = run_migrate(
        Clients(
            discourse=discourse_api,
            repository=repository_client,
        ),
        user_inputs=factories.UserInputsFactory(commit_sha=repository_client.current_commit),
    )

    upstream_git_repo.git.checkout(DEFAULT_BRANCH_NAME)
    upstream_doc_dir = upstream_repository_path / constants.DOCUMENTATION_FOLDER_NAME
    assert output_migrate.pull_request_url == mock_pull_request.html_url
    assert output_migrate.action == PullRequestAction.OPENED
    assert (group_1_path := upstream_doc_dir / "group-1").is_dir()
    assert (group_1_path / migration.GITKEEP_FILENAME).is_file()
    assert (group_2_path := upstream_doc_dir / "group-2").is_dir()
    assert (group_2_path / "content-1.md").read_text(encoding="utf-8") == content_page_1.content
    assert (group_2_path / "content-2.md").read_text(encoding="utf-8") == content_page_2.content
    assert (group_3_path := upstream_doc_dir / "group-3").is_dir()
    assert (group_4_path := group_3_path / "group-4").is_dir()
    assert (group_4_path / "content-3.md").read_text(encoding="utf-8") == content_page_3.content
    assert (group_3_path / "content-4.md").read_text(encoding="utf-8") == content_page_4.content
    assert (group_5_path := upstream_doc_dir / "group-5").is_dir()
    assert group_5_path.is_dir()
    upstream_git_repo.git.checkout(BASE_REMOTE_BRANCH)

    # 2. with no changes applied after raising PR
    caplog.clear()

    mock_github_repo.get_pulls.return_value = [mock_pull_request]

    output_migrate = run_migrate(
        Clients(
            discourse=discourse_api,
            repository=RepositoryClient(Repo(repository_path), mock_github_repo),
        ),
        user_inputs=factories.UserInputsFactory(commit_sha=repository_client.current_commit),
    )

    assert "test_url" in output_migrate.pull_request_url
    assert output_migrate.action == PullRequestAction.UPDATED
    assert_substrings_in_string(
        ["upload-charm-documents pull request already open at test_url"], caplog.text
    )

    # 3. Add modification to an existing open PR
    caplog.clear()

    discourse_api.update_topic(content_page_2_url, content_page_2.content + " updated")

    output_migrate = run_migrate(
        Clients(
            discourse=discourse_api,
            repository=RepositoryClient(Repo(repository_path), mock_github_repo),
        ),
        user_inputs=factories.UserInputsFactory(commit_sha=repository_client.current_commit),
    )

    assert "test_url" in output_migrate.pull_request_url
    assert output_migrate.action == PullRequestAction.UPDATED
    assert_substrings_in_string(
        [
            "upload-charm-documents pull request already open at test_url",
            "Updating PR with new commit",
        ],
        caplog.text,
    )

    # Simulate a PR merged
    upstream_git_repo.git.checkout(DEFAULT_BRANCH)
    upstream_git_repo.git.merge(DEFAULT_BRANCH_NAME)

    repository_client.switch(DEFAULT_BRANCH).pull()
    repository_client.tag_commit(DOCUMENTATION_TAG, repository_client.current_commit)

    mock_github_repo.get_pulls.return_value = [mock_pull_request]

    # 4. Content in sync with Discourse
    caplog.clear()

    discourse_api.update_topic(content_page_2_url, content_page_2.content + " updated")

    def mock_edit(*args, **kwargs):  # pylint: disable=W0613
        """Mock edit method for the PullRequest object.

        Args:
            args: positional arguments
            kwargs: keyword arguments
        """
        assert kwargs["state"] == "closed"

    monkeypatch.setattr(PullRequest, "edit", mock_edit)

    output_migrate = run_migrate(
        Clients(
            discourse=discourse_api,
            repository=RepositoryClient(Repo(repository_path), mock_github_repo),
        ),
        user_inputs=factories.UserInputsFactory(commit_sha=repository_client.current_commit),
    )

    assert output_migrate
    assert output_migrate.action == PullRequestAction.CLOSED
    assert_substrings_in_string(
        [
            "No community contribution found in commit",
            f"Discourse is inline with {DOCUMENTATION_TAG}",
        ],
        caplog.text,
    )
