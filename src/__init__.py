# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for uploading docs to charmhub."""

from itertools import tee
from pathlib import Path

from .action import DRY_RUN_NAVLINK_LINK, FAIL_NAVLINK_LINK
from .action import run_all as run_all_actions
from .check import conflicts as check_conflicts
from .constants import DOCUMENTATION_FOLDER_NAME
from .pull_request import DEFAULT_BRANCH_NAME
from .discourse import Discourse
from .docs_directory import has_docs_directory
from .docs_directory import read as read_docs_directory
from .exceptions import InputError
from .index import contents_from_page
from .index import get as get_index
from .metadata import get as get_metadata
from .migration import run as migrate_contents
from .navigation_table import from_page as navigation_table_from_page
from .pull_request import create_pull_request
from .reconcile import run as run_reconcile
from .repository import create_repository_client
from .types_ import ActionResult, Clients, Metadata, UserInputs

GETTING_STARTED = (
    "To get started with upload-charm-docs, "
    "please refer to https://github.com/canonical/upload-charm-docs#getting-started"
)


def run_reconcile(
    clients: Clients, user_inputs: UserInputs
) -> dict[str, str]:
    """Upload the documentation to charmhub.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        All the URLs that had an action with the result of that action.

    Raises:
        InputError: if there are any problems with executing any of the actions.

    """
    metadata = clients.repository.metadata
    base_path = clients.repository.base_path

    index = get_index(metadata=metadata, base_path=base_path, server_client=clients.discourse)
    path_infos = read_docs_directory(docs_path=base_path / DOCUMENTATION_FOLDER_NAME)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    table_rows = navigation_table_from_page(page=server_content, discourse=clients.discourse)
    actions = run_reconcile(
        path_infos=path_infos,
        table_rows=table_rows,
        clients=clients,
        base_path=base_path,
        user_inputs=user_inputs,
    )

    # tee creates a copy of the iterator which is needed as check_conflicts consumes the iterator
    # it is passed
    actions, check_actions = tee(actions, 2)
    problems = tuple(check_conflicts(actions=check_actions))
    if problems:
        raise InputError(
            "One or more of the required actions could not be executed, see the log for details"
        )

    reports = run_all_actions(
        actions=actions,
        index=index,
        discourse=clients.discourse,
        dry_run=user_inputs.dry_run,
        delete_pages=user_inputs.delete_pages,
    )
    urls_with_actions: dict[str, str] = {
        str(report.location): report.result
        for report in reports
        if report.location is not None
        and report.location != DRY_RUN_NAVLINK_LINK
        and report.location != FAIL_NAVLINK_LINK
    }

    if not user_inputs.dry_run:
        clients.repository.tag_commit(
            tag_name=user_inputs.base_tag_name, commit_sha=user_inputs.commit_sha
        )

    return urls_with_actions


def run_migrate(clients: Clients, user_inputs: UserInputs) -> dict[str, str]:
    """Migrate existing docs from charmhub to local repository.

    Args:
        clients: The clients to interact with things like discourse and the repository.

    Returns:
        A single key-value pair dictionary containing a link to the Pull Request containing
        migrated documentation as key and successful action result as value.
    """

    # Remove docs folder and recreate content from discourse
    base_path = clients.repository.base_path
    metadata = clients.repository.metadata

    docs_path = base_path / DOCUMENTATION_FOLDER_NAME

    if docs_path.exists():
        docs_path.rmdir()

    index = get_index(metadata=metadata, base_path=base_path, server_client=clients.discourse)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    index_content = contents_from_page(server_content)
    table_rows = navigation_table_from_page(page=server_content, discourse=clients.discourse)
    migrate_contents(
        table_rows=table_rows,
        index_content=index_content,
        discourse=clients.discourse,
        docs_path=base_path / DOCUMENTATION_FOLDER_NAME,
    )

    # Check difference with main
    if not clients.repository.is_dirty(user_inputs.base_branch):
        return {}

    pull_request = clients.repository.get_pull_request(DEFAULT_BRANCH_NAME)

    if pull_request is not None:
        with clients.repository.with_branch(DEFAULT_BRANCH_NAME) as repo:
            if repo.is_dirty():
                repo.update_branch("time and date or relevant message")
    else:
        with clients.repository.create_branch(
            DEFAULT_BRANCH_NAME, user_inputs.base_branch
        ).with_branch(DEFAULT_BRANCH_NAME) as repo:
            repo.update_branch("time and date or relevant message",force=True)
            pull_request = repo.create_pull_request(DEFAULT_BRANCH_NAME)

    return {pull_request: ActionResult.SUCCESS}


