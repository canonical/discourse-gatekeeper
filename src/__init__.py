# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for uploading docs to charmhub."""
import logging
from itertools import tee
import shutil

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
from .pull_request import DEFAULT_BRANCH_NAME
from .pull_request import create_pull_request
from .reconcile import run as run_reconcile, Clients
from .repository import create_repository_client
from .types_ import ActionResult, Metadata, UserInputs

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
    return {
        str(report.location): report.result
        for report in reports
        if report.location is not None
           and report.location != DRY_RUN_NAVLINK_LINK
           and report.location != FAIL_NAVLINK_LINK
    }


def download_from_discourse(clients: Clients) -> None:
    base_path = clients.repository.base_path
    metadata = clients.repository.metadata

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



def run_migrate(clients: Clients, user_inputs: UserInputs) -> dict[str, str]:
    """Migrate existing docs from charmhub to local repository.

    Args:
        clients: The clients to interact with things like discourse and the repository.

    Returns:
        A single key-value pair dictionary containing a link to the Pull Request containing
        migrated documentation as key and successful action result as value.
    """

    # Remove docs folder and recreate content from discourse
    clients.repository.switch(user_inputs.base_branch).pull()

    docs_path = clients.repository.base_path / DOCUMENTATION_FOLDER_NAME

    if docs_path.exists():
        shutil.rmtree(docs_path)

    download_from_discourse(clients)

    # Check difference with main
    if not clients.repository.is_dirty(user_inputs.base_branch):
        logging.info(
            f"No community contribution found. Discourse is inline with {user_inputs.base_branch}"
        )
        return {}

    pr_link = clients.repository.get_pull_request(DEFAULT_BRANCH_NAME)

    if pr_link is not None:
        logging.info(f"upload-charm-documents pull request already open at {pr_link}")
        with clients.repository.with_branch(DEFAULT_BRANCH_NAME) as repo:
            if repo.is_dirty():
                msg = str(repo.summary)
                logging.info(f"Updating PR with new commit: {msg}")
                repo.update_branch(msg)
    else:
        with clients.repository.create_branch(
                DEFAULT_BRANCH_NAME, user_inputs.base_branch
        ).with_branch(DEFAULT_BRANCH_NAME) as repo:
            msg = str(repo.summary)
            logging.info(f"Creating new branch with new commit: {msg}")
            repo.update_branch(msg, force=True)
            pr_link = repo.create_pull_request(DEFAULT_BRANCH_NAME)
            logging.info(f"Opening new PR with community contribution: {pr_link}")

    return {pr_link: ActionResult.SUCCESS}
