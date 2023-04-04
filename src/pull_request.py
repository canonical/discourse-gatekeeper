# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling interactions with git repository."""

import logging

from .exceptions import InputError
from .repository import Client as RepositoryClient

BRANCH_PREFIX = "upload-charm-docs"
DEFAULT_BRANCH_NAME = f"{BRANCH_PREFIX}/migrate"
ACTIONS_COMMIT_MESSAGE = "migrate docs from server"


def create_pull_request(repository: RepositoryClient) -> str:
    """Create pull request for changes in given repository path.

    Args:
        repository: A git client to interact with local and remote git repository.

    Raises:
        InputError: if pull request branch name is invalid or the a branch
        with same name already exists.

    Returns:
        Pull request URL string. None if no pull request was created/modified.
    """
    if not repository.is_dirty():
        raise InputError("No files seem to be migrated. Please add contents upstream first.")
    if repository.check_branch_exists(branch_name=DEFAULT_BRANCH_NAME):
        raise InputError(
            f"Branch {DEFAULT_BRANCH_NAME} already exists."
            f"Please try again after removing {DEFAULT_BRANCH_NAME}."
        )

    logging.info("create new branch %s", DEFAULT_BRANCH_NAME)
    repository.create_branch(
        branch_name=DEFAULT_BRANCH_NAME,
        commit_msg=ACTIONS_COMMIT_MESSAGE,
    )
    logging.info("create pull request %s", DEFAULT_BRANCH_NAME)
    pull_request_web_link = repository.create_pull_request(branch_name=DEFAULT_BRANCH_NAME)

    return pull_request_web_link
