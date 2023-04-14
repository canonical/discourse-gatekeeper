# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling interactions with git repository."""

import logging

from .repository import Client as RepositoryClient

BRANCH_PREFIX = "upload-charm-docs"
DEFAULT_BRANCH_NAME = f"{BRANCH_PREFIX}/migrate"
ACTIONS_COMMIT_MESSAGE = "migrate docs from server"


def create_pull_request(repository: RepositoryClient, base: str) -> str:
    """Create pull request for changes in given repository path.

    Args:
        repository: A git client to interact with local and remote git repository.
        base: base branch or tag against to which the PR is opened

    Returns:
        Pull request URL string. None if no pull request was created/modified.
    """
    with repository.create_branch(
            DEFAULT_BRANCH_NAME, base
    ).with_branch(DEFAULT_BRANCH_NAME) as repo:
        msg = str(repo.summary)
        logging.info(f"Creating new branch with new commit: {msg}")
        repo.update_branch(msg, force=True)
        pr_link = repo.create_pull_request(DEFAULT_BRANCH_NAME)
        logging.info(f"Opening new PR with community contribution: {pr_link}")

    return pr_link


def update_pull_request(repository: RepositoryClient, branch: str) -> None:
    with repository.with_branch(branch) as repo:
        if repo.is_dirty():
            repo.pull()
            msg = str(repo.summary)
            logging.info(f"Updating PR with new commit: {msg}")
            repo.update_branch(msg)
