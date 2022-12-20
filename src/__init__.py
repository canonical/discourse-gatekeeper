# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for uploading docs to charmhub."""

from pathlib import Path

from git.repo import Repo
from github.Repository import Repository

from .action import DRY_RUN_NAVLINK_LINK, FAIL_NAVLINK_LINK
from .action import run_all as run_all_actions
from .discourse import Discourse
from .docs_directory import has_docs_directory
from .docs_directory import read as read_docs_directory
from .exceptions import InputError
from .index import DOCUMENTATION_FOLDER_NAME, contents_from_page
from .index import get as get_index
from .metadata import get as get_metadata
from .migration import get_docs_metadata
from .migration import run as run_migrate
from .navigation_table import from_page as navigation_table_from_page
from .pull_request import create_pull_request
from .reconcile import run as run_reconcile
from .types_ import ActionResult, Metadata

GETTING_STARTED = (
    "To get started with upload-charm-docs, "
    "please refer to https://github.com/canonical/upload-charm-docs#getting-started"
)


def _run_reconcile(
    base_path: Path,
    metadata: Metadata,
    discourse: Discourse,
    dry_run: bool,
    delete_pages: bool,
) -> dict[str, str]:
    """Upload the documentation to charmhub.

    Args:
        base_path: The base path to look for the metadata file in.
        discourse: A client to the documentation server.
        dry_run: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        All the URLs that had an action with the result of that action.

    """
    index = get_index(metadata=metadata, base_path=base_path, server_client=discourse)
    path_infos = read_docs_directory(docs_path=base_path / DOCUMENTATION_FOLDER_NAME)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    table_rows = navigation_table_from_page(page=server_content)
    actions = run_reconcile(path_infos=path_infos, table_rows=table_rows, discourse=discourse)
    reports = run_all_actions(
        actions=actions,
        index=index,
        discourse=discourse,
        dry_run=dry_run,
        delete_pages=delete_pages,
    )
    return {
        report.url: report.result
        for report in reports
        if report.url is not None
        and report.url != DRY_RUN_NAVLINK_LINK
        and report.url != FAIL_NAVLINK_LINK
    }


# pylint: disable=too-many-arguments
def _run_migrate(
    base_path: Path,
    metadata: Metadata,
    discourse: Discourse,
    repo: Repo,
    github_repo: Repository,
    branch_name: str | None,
) -> dict[str, str]:
    """Migrate existing docs from charmhub to local repository.

    Returns:
        All the filepaths that were created with the result of that action.
    """
    index = get_index(metadata=metadata, base_path=base_path, server_client=discourse)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    index_content = contents_from_page(server_content)
    table_rows = navigation_table_from_page(page=server_content)
    file_metadata = get_docs_metadata(table_rows=table_rows, index_content=index_content)
    run_migrate(
        documents=file_metadata,
        discourse=discourse,
        docs_path=base_path / DOCUMENTATION_FOLDER_NAME,
    )

    pr_link = create_pull_request(
        repository=repo, github_repository=github_repo, branch_name=branch_name
    )

    return {pr_link: ActionResult.SUCCESS}


def run(
    base_path: Path,
    discourse: Discourse,
    dry_run: bool,
    delete_pages: bool,
    repo: Repo,
    github_repo: Repository,
    branch_name: str | None,
) -> dict[str, str]:
    """Interact with charmhub to upload documentation or migrate to local repository.

    Args:
        base_path: The base path to look for the metadata file in.
        discourse: A client to the documentation server.
        dry_run: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        All the URLs that had an action with the result of that action.
    """
    metadata = get_metadata(base_path)
    has_docs_dir = has_docs_directory(base_path=base_path)
    if metadata.docs and not has_docs_dir:
        return _run_migrate(
            base_path=base_path,
            metadata=metadata,
            discourse=discourse,
            repo=repo,
            github_repo=github_repo,
            branch_name=branch_name,
        )
    if has_docs_dir:
        return _run_reconcile(
            base_path=base_path,
            metadata=metadata,
            discourse=discourse,
            dry_run=dry_run,
            delete_pages=delete_pages,
        )
    raise InputError(GETTING_STARTED)
