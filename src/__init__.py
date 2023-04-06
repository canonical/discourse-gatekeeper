# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for uploading docs to charmhub."""

from itertools import tee
from pathlib import Path

from .action import DRY_RUN_NAVLINK_LINK, FAIL_NAVLINK_LINK
from .action import run_all as run_all_actions
from .check import conflicts as check_conflicts
from .constants import DOCUMENTATION_FOLDER_NAME
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


def _run_reconcile(
    base_path: Path, metadata: Metadata, clients: Clients, user_inputs: UserInputs
) -> dict[str, str]:
    """Upload the documentation to charmhub.

    Args:
        base_path: The base path of the repository.
        metadata: Information about the charm.
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        All the URLs that had an action with the result of that action.

    Raises:
        InputError: if there are any problems with executing any of the actions.

    """
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
    return {
        str(report.location): report.result
        for report in reports
        if report.location is not None
        and report.location != DRY_RUN_NAVLINK_LINK
        and report.location != FAIL_NAVLINK_LINK
    }


def _run_migrate(base_path: Path, metadata: Metadata, clients: Clients) -> dict[str, str]:
    """Migrate existing docs from charmhub to local repository.

    Args:
        base_path: The base path of the repository.
        metadata: Information about the charm.
        clients: The clients to interact with things like discourse and the repository.

    Returns:
        A single key-value pair dictionary containing a link to the Pull Request containing
        migrated documentation as key and successful action result as value.
    """

    # Remove docs folder and recreate content from discourse
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
    if not repository.is_dirty(default_branch):
        return ...

    pull_request = repository.get_or_create_pull_request("upload-charm-docs/migrate")

    if repository.is_dirty(pull_request.head.ref):
        repository.update_branch("time and date or relevant message")

    # pr_link = create_pull_request(repository=repository)

    return {pr_link: ActionResult.SUCCESS}


def run(base_path: Path, discourse: Discourse, user_inputs: UserInputs) -> dict[str, str]:
    """Interact with charmhub to upload documentation or migrate to local repository.

    Args:
        base_path: The base path to look for the metadata file in.
        discourse: A client to the documentation server.
        user_inputs: Configurable inputs for running upload-charm-docs.

    Raises:
        InputError: if no valid running mode is matched.

    Returns:
        All the URLs that had an action with the result of that action.
    """
    metadata = get_metadata(base_path)
    has_docs_dir = has_docs_directory(base_path=base_path)
    repository = create_repository_client(
        access_token=user_inputs.github_access_token, base_path=base_path
    )
    clients = Clients(discourse=discourse, repository=repository)

    # Run this only if the reference to discourse exists
    if metadata.docs:
        return _run_migrate(
            base_path=base_path,
            metadata=metadata,
            clients=clients
        )
    if has_docs_dir:
        return _run_reconcile(
            base_path=base_path, metadata=metadata, clients=clients, user_inputs=user_inputs
        )
    raise InputError(GETTING_STARTED)
