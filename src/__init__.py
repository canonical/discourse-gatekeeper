# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for uploading docs to charmhub."""
import logging
from itertools import tee

from src import action, check, docs_directory
from src import index as index_module
from src import navigation_table, reconcile
from src import sort as sort_module
from src.action import DRY_RUN_NAVLINK_LINK, FAIL_NAVLINK_LINK
from src.clients import Clients
from src.constants import DOCUMENTATION_FOLDER_NAME, DOCUMENTATION_TAG
from src.download import recreate_docs
from src.exceptions import InputError, TaggingNotAllowedError
from src.repository import DEFAULT_BRANCH_NAME
from src.types_ import (
    ActionResult,
    MigrateOutputs,
    PullRequestAction,
    ReconcileOutputs,
    Url,
    UserInputs,
)

GETTING_STARTED = (
    "To get started with discourse-gatekeeper, "
    "please refer to https://github.com/canonical/discourse-gatekeeper#getting-started"
)


def run_reconcile(clients: Clients, user_inputs: UserInputs) -> ReconcileOutputs | None:
    """Upload the documentation to charmhub.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running discourse-gatekeeper.

    Returns:
        ReconcileOutputs object with the result of the action. None, if there is no reconcile.

    Raises:
        InputError: if there are any problems with executing any of the actions.
        TaggingNotAllowedError: if the reconcile tries to tag a branch which is not the main base
            branch
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
    index_contents, check_index_contents = tee(index_contents, 2)
    problems = tuple(check.external_refs(index_contents=check_index_contents))
    if problems:
        raise InputError(
            "One or more of the contents index entries are not valid, see the log for details"
        )

    sorted_path_infos = sort_module.using_contents_index(
        path_infos=path_infos, index_contents=index_contents, docs_path=docs_path
    )
    table_rows = list(navigation_table.from_page(page=server_content, discourse=clients.discourse))
    actions = reconcile.run(
        sorted_path_infos=sorted_path_infos,
        table_rows=table_rows,
        clients=clients,
        base_path=clients.repository.base_path,
    )

    # tee creates a copy of the iterator which is needed as check.conflicts consumes the iterator
    # it is passed
    actions, check_actions = tee(actions, 2)
    if reconcile.is_same_content(index, check_actions):
        logging.info(
            "Reconcile not required to run as the content is the same on Discourse and Github."
        )
        if clients.repository.is_commit_in_branch(user_inputs.commit_sha, user_inputs.base_branch):
            # This means we are running from the base_branch
            logging.info(
                "Updating the tag %s on commit %s", DOCUMENTATION_TAG, user_inputs.commit_sha
            )
            clients.repository.tag_commit(DOCUMENTATION_TAG, user_inputs.commit_sha)

        return ReconcileOutputs(
            index_url=index.server.url if index.server else "",
            topics=(
                {
                    f"{clients.discourse.absolute_url(row.navlink.link)}": ActionResult.SKIP
                    for row in table_rows
                    if row.navlink.link
                }
            )
            | (
                {clients.discourse.absolute_url(index.server.url): ActionResult.SKIP}
                if index.server
                else {}
            ),
            documentation_tag=clients.repository.tag_exists(DOCUMENTATION_TAG),
        )

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
        # Make sure that tags are applied only to base_branches
        if not clients.repository.is_commit_in_branch(
            user_inputs.commit_sha, user_inputs.base_branch
        ):
            raise TaggingNotAllowedError(
                f"{user_inputs.commit_sha} outside of {user_inputs.base_branch}"
            )

        clients.repository.tag_commit(
            tag_name=DOCUMENTATION_TAG, commit_sha=user_inputs.commit_sha
        )

    return ReconcileOutputs(
        index_url=index_url,
        topics=urls_with_actions,
        documentation_tag=clients.repository.tag_exists(DOCUMENTATION_TAG),
    )


def run_migrate(clients: Clients, user_inputs: UserInputs) -> MigrateOutputs | None:
    """Migrate existing docs from charmhub to local repository.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running discourse-gatekeeper.

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
                action=PullRequestAction.CLOSED, pull_request_url=pull_request.html_url
            )
        return None

    if pull_request is None:
        logging.info("PR not existing: creating a new one...")
        pull_request = clients.repository.create_pull_request(user_inputs.base_branch)
        return MigrateOutputs(
            action=PullRequestAction.OPENED, pull_request_url=pull_request.html_url
        )

    logging.info("discourse-gatekeeper pull request already open at %s", pull_request.html_url)
    clients.repository.update_pull_request(DEFAULT_BRANCH_NAME)

    return MigrateOutputs(action=PullRequestAction.UPDATED, pull_request_url=pull_request.html_url)


def pre_flight_checks(clients: Clients, user_inputs: UserInputs) -> bool:
    """Perform checks to make sure the repository is in a consistent state.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running discourse-gatekeeper.

    Returns:
        Boolean representing whether the checks have all been passed.
    """
    clients.repository.switch(user_inputs.base_branch)

    documentation_commit = clients.repository.tag_exists(DOCUMENTATION_TAG)

    if not documentation_commit:
        logging.info(
            "documentation tag %s does not exists. Creating at commit %s",
            DOCUMENTATION_TAG,
            clients.repository.current_commit,
        )
        clients.repository.tag_commit(DOCUMENTATION_TAG, clients.repository.current_commit)
        return True

    commit_in_branch = clients.repository.is_commit_in_branch(
        documentation_commit, user_inputs.base_branch
    )
    if not commit_in_branch:
        logging.error(
            "Inconsistent repository: documentation tag %s (at commit %s)"
            " not in base branch %s",
            DOCUMENTATION_TAG,
            documentation_commit,
            user_inputs.base_branch,
        )
    return commit_in_branch
