# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling interactions with git repository."""

import logging

from .exceptions import InputError
from .repository import Client as RepositoryClient

BRANCH_PREFIX = "upload-charm-docs"
DEFAULT_BRANCH_NAME = f"{BRANCH_PREFIX}/migrate"
ACTIONS_COMMIT_MESSAGE = "migrate docs from server"


def create_pull_request(repository: RepositoryClient, base: str) -> str:
    """Create pull request for changes in given repository path.

    Args:
        repository: A git client to interact with local and remote git repository.
        base: base branch or tag against to which the PR is opened

    Raises:
        InputError: when the repository is not dirty, hence resulting on an empty pull-request

    Returns:
        Pull request URL string. None if no pull request was created/modified.
    """
    if not repository.is_dirty(base):
        raise InputError("No files seem to be migrated. Please add contents upstream first.")

    with repository.create_branch(DEFAULT_BRANCH_NAME, base).with_branch(
        DEFAULT_BRANCH_NAME
    ) as repo:
        logging.info(repo._git_repo.git.status())
        msg = str(repo.summary)
        logging.info("Creating new branch with new commit: %s", msg)
        repo.update_branch(msg, force=True)
        pr_link = repo.create_pull_request(DEFAULT_BRANCH_NAME)
        logging.info("Opening new PR with community contribution: %s", pr_link)

    return pr_link


def update_pull_request(repository: RepositoryClient, branch: str) -> None:
    """Update and push changes to the given branch.

    Args:
        repository: RepositoryClient object
        branch: name of the branch to be updated
    """
    with repository.with_branch(branch) as repo:
        if repo.is_dirty():
            repo.pull()
            msg = str(repo.summary)
            logging.info(f"Summary: {msg}")
            logging.info("Updating PR with new commit: %s", msg)
            repo.update_branch(msg)
