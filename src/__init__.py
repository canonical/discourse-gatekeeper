# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for uploading docs to charmhub."""
import logging
from itertools import tee

from . import action, check, docs_directory
from . import index as index_module
from . import navigation_table, reconcile
from . import sort as sort_module
from .action import DRY_RUN_NAVLINK_LINK, FAIL_NAVLINK_LINK
from .clients import Clients
from .constants import DOCUMENTATION_FOLDER_NAME, DOCUMENTATION_TAG  # DEFAULT_BRANCH,
from .docs_directory import read as read_docs_directory
from .download import recreate_docs
from .exceptions import InputError
from .repository import DEFAULT_BRANCH_NAME
from .types_ import (
    ActionResult, UserInputs, PullRequestAction, ReconcileOutputs, MigrateOutputs, Url
)

GETTING_STARTED = (
    "To get started with upload-charm-docs, "
    "please refer to https://github.com/canonical/upload-charm-docs#getting-started"
)


def run_reconcile(clients: Clients, user_inputs: UserInputs) -> ReconcileOutputs | None:
    """Upload the documentation to charmhub.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        ReconcileOutputs object with the result of the action. None, if there is no reconcile.

    Raises:
        InputError: if there are any problems with executing any of the actions.

    """
    if not clients.repository.has_docs_directory:
        logging.warning(
            "Cannot run any reconcile to Discourse as there is not any docs folder "
            "present in the repository"
        )

        return None

    if clients.repository.is_same_commit(DOCUMENTATION_TAG, user_inputs.commit_sha):
        logging.warning(
            "Cannot run any reconcile to Discourse as we are at the same commit of the tag %s",
            DOCUMENTATION_TAG,
        )
        return None

    index = index_module.get(
        metadata=clients.repository.metadata,
        base_path=clients.repository.base_path,
        server_client=clients.discourse,
    )
    docs_path = clients.repository.base_path / DOCUMENTATION_FOLDER_NAME
    path_infos = docs_directory.read(docs_path=docs_path)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    index_contents = index_module.get_contents(index_file=index.local, docs_path=docs_path)
    sorted_path_infos = sort_module.using_contents_index(
        path_infos=path_infos, index_contents=index_contents, docs_path=docs_path
    )
    table_rows = navigation_table.from_page(page=server_content, discourse=clients.discourse)
    actions = reconcile.run(
        sorted_path_infos=sorted_path_infos,
        table_rows=table_rows,
        clients=clients,
        base_path=clients.repository.base_path,
    )

    # tee creates a copy of the iterator which is needed as check.conflicts consumes the iterator
    # it is passed
    actions, check_actions = tee(actions, 2)
    problems = tuple(
        check.conflicts(
            actions=check_actions, repository=clients.repository, user_inputs=user_inputs
        )
    )
    if problems:
        raise InputError(
            "One or more of the required actions could not be executed, see the log for details"
        )

    index_url, reports = action.run_all(
        actions=actions,
        index=index,
        discourse=clients.discourse,
        dry_run=user_inputs.dry_run,
        delete_pages=user_inputs.delete_pages,
    )
    urls_with_actions: dict[Url, ActionResult] = {
        str(report.location): report.result
        for report in reports
        if report.location is not None
           and report.location != DRY_RUN_NAVLINK_LINK
           and report.location != FAIL_NAVLINK_LINK
    }

    if not user_inputs.dry_run:
        clients.repository.tag_commit(
            tag_name=DOCUMENTATION_TAG, commit_sha=user_inputs.commit_sha
        )

    return ReconcileOutputs(
        index_url=index_url,
        topics=urls_with_actions,
        documentation_tag=clients.repository.tag_exists(DOCUMENTATION_TAG)
    )


def run_migrate(clients: Clients, user_inputs: UserInputs) -> MigrateOutputs | None:
    """Migrate existing docs from charmhub to local repository.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        MigrateOutputs providing details on the action performed and a link to the
        Pull Request containing migrated documentation. None if there is no migration.
    """
    if not clients.repository.metadata.docs:
        logging.warning(
            "Cannot run migration from Discourse as there is no discourse "
            "link available in metadata"
        )
        return None

    logging.info("Tag exists: %s", str(clients.repository.tag_exists(DOCUMENTATION_TAG)))

    if not clients.repository.tag_exists(DOCUMENTATION_TAG):
        with clients.repository.with_branch(user_inputs.base_branch) as repo:
            main_hash = repo.current_commit
        clients.repository.tag_commit(DOCUMENTATION_TAG, main_hash)

    pull_request = clients.repository.get_pull_request(DEFAULT_BRANCH_NAME)

    # Check difference with main
    changes = recreate_docs(clients, DOCUMENTATION_TAG)
    if not changes:
        logging.info(
            "No community contribution found in commit %s. Discourse is inline with %s",
            user_inputs.commit_sha,
            DOCUMENTATION_TAG,
        )
        # Given there are NO diffs compared to the base, if a PR is open, it should be closed
        if pull_request is not None:
            pull_request.edit(state="closed")
            return MigrateOutputs(
                action=PullRequestAction.CLOSED,
                pull_request_url=pull_request.html_url
            )
        return None

    if pull_request is None:
        logging.info("PR not existing: creating a new one...")
        pull_request = clients.repository.create_pull_request(user_inputs.base_branch)
        return MigrateOutputs(
            action=PullRequestAction.OPENED,
            pull_request_url=pull_request.html_url
        )

    logging.info("upload-charm-documents pull request already open at %s", pull_request.html_url)
    clients.repository.update_pull_request(DEFAULT_BRANCH_NAME)

    return MigrateOutputs(action=PullRequestAction.UPDATED, pull_request_url=pull_request.html_url)


def pre_flight_checks(clients: Clients, user_inputs: UserInputs) -> bool:
    """Perform checks to make sure the repository is in a consistent state.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        Boolean representing whether the checks have all been passed.
    """
    with clients.repository.with_branch(user_inputs.base_branch) as repo:
        if repo.tag_exists(DOCUMENTATION_TAG):
            return repo.is_commit_in_branch(
                repo.switch(DOCUMENTATION_TAG).current_commit, user_inputs.base_branch
            )
        repo.tag_commit(DOCUMENTATION_TAG, repo.current_commit)
