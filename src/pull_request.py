# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling git repository."""

import logging
import re
import typing
from uuid import uuid4

from git import GitCommandError
from git.repo import Repo
from github import Github
from github.Repository import Repository

from .exceptions import GitError, InputError

GITHUB_HOSTNAME = "github.com"
HTTPS_URL_PATTERN = re.compile(rf"^https?:\/\/.*@?{GITHUB_HOSTNAME}\/(.+\/.+?)(.git)?$")
ACTIONS_USER_NAME = "actions-bot"
ACTIONS_USER_EMAIL = "actions-bot@users.noreply.github.com"
ACTIONS_COMMIT_MESSAGE = "migrate docs from server"
ACTIONS_PULL_REQUEST_TITLE = "[docs] Migrate charm docs"
ACTIONS_PULL_REQUEST_BODY = "This pull request was autogenerated by upload-charm-docs"
PR_LINK_NO_CHANGE = "<not created due to no changes in repository>"
PR_LINK_DRY_RUN = "<not created due in dry run mode>"
DEFAULT_BRANCH_NAME = "upload-charm-docs"


def _configure_user(repository: Repo):
    """Configure action git profile defaults."""
    config_writer = repository.config_writer()
    config_writer.set_value("user", "name", ACTIONS_USER_NAME)
    config_writer.set_value("user", "email", ACTIONS_USER_EMAIL)
    config_writer.release()


def _check_branch_exists(repository: Repo, branch_name: str):
    """Check if branch exists on remote.

    Args:
        repository: Git-binding for the current repository.
        branch_name: Branch name to check on remote.

    Returns:
        True if branch already exists, False otherwise.
    """
    try:
        repository.git.fetch("origin", branch_name)
        return True
    except GitCommandError as exc:
        if "couldn't find remote ref" in exc.stderr:
            return False
        raise exc


def _merge_existing_branch(repository: Repo, branch_name: str, commit_msg: str, dry_run: bool):
    """Merge existing changes in current repository with specified branch with theirs strategy.

    Args:
        repository: Git-binding for the current repository.
        branch_name: Base branch to merge to.
        commit_msg: Commit message for current changes.
        dry_run: If enabled, only log the action that would be taken.
    """
    logging.info("dry run: %s, merge to existing branch %s", dry_run, branch_name)
    temp_branch = str(uuid4())
    head = repository.create_head(temp_branch)
    head.checkout()
    repository.git.add(".")
    repository.git.commit("-m", f"'{commit_msg}'")

    repository.git.checkout(branch_name)
    repository.git.pull()
    repository.git.merge(temp_branch, "-Xtheirs", "--squash", "--no-edit")
    repository.git.commit("-m", f"'{commit_msg}'")

    if not dry_run:
        repository.git.push("-u", "origin", branch_name)

    repository.git.branch("-D", temp_branch)


def _create_branch(repository: Repo, branch_name: str, commit_msg: str, dry_run: bool):
    """Create new branch with existing changes.

    Args:
        repository: Current repository.
        branch_name: New branch name.
        commit_msg: Commit message for current changes.
    """
    logging.info("dry run: %s, create new branch %s", dry_run, branch_name)
    repository.git.checkout("-b", branch_name)
    repository.git.add(".")
    repository.git.commit("-m", f"'{commit_msg}'")

    if not dry_run:
        repository.git.push("-u", "origin", branch_name)


def _create_pull_request(
    github_repository: Repository, branch_name: str, base: str, dry_run: bool
):
    """Create a pull request.

    Args:
        github_repository: Github repository client.
        branch_name: Branch name from which the pull request will be created.
        base: Base branch to which the pull request will be created.
        dry_run: If enabled, only log the action that would be taken.

    Returns:
        The pull request URL.
    """
    logging.info("dry run: %s, create pull request %s", dry_run, branch_name)
    if not dry_run:
        pull_request = github_repository.create_pull(
            title=ACTIONS_PULL_REQUEST_TITLE,
            body=ACTIONS_PULL_REQUEST_BODY,
            base=base,
            head=branch_name,
        )
    else:
        pull_request = None
    return pull_request.url if pull_request is not None else PR_LINK_DRY_RUN


def get_repository_name(remote_url: str):
    """Get repository name.

    Args:
        remote_url: URL of remote repository. \
            e.g. https://github.com/canonical/upload-charm-docs.git

    Raises:
        GitError if invalid remote url.

    Returns:
        Git repository name. e.g. canonical/upload-charm-docs.
    """
    matched_repository = HTTPS_URL_PATTERN.match(remote_url)
    if not matched_repository:
        raise GitError(f"Invalid remote repository name {remote_url=!r}")
    return matched_repository.group(1)


def create_github(access_token: typing.Any):
    """Create a Github instance to handle communication with Github server.

    Args:
        access_token: Access token that has permissions to open a pull request.

    Raises:
        InputError: if invalid token format input.

    Returns:
        A Github repository instance.
    """
    if not access_token:
        raise InputError(
            f"Invalid 'access_token' input, it must be non-empty, got {access_token=!r}"
        )
    if not isinstance(access_token, str):
        raise InputError(
            f"Invalid 'access_token' input, it must be a string, got {access_token=!r}"
        )

    return Github(login_or_token=access_token)


def create_pull_request(
    repository: Repo,
    github_repository: Repository,
    branch_name: str | None,
    dry_run: bool,
) -> str:
    """Create pull request for changes in given repository path.

    Args:
        access_token: Github access token.
        repository_path: Repository root where .git resides.
        branch_name: Pull request branch name.

    Raises:
        InputError: if branch name configuration is invalid.

    Returns:
        Pull request URL string. None if no pull request was created/modified.
    """
    branch_name = branch_name or DEFAULT_BRANCH_NAME
    base = repository.active_branch.name
    if base == branch_name:
        raise InputError("Branch name cannot be equal to base branch.")

    if not repository.is_dirty(untracked_files=True):
        return PR_LINK_NO_CHANGE

    _configure_user(repository=repository)

    if _check_branch_exists(repository=repository, branch_name=branch_name):
        _merge_existing_branch(
            repository=repository,
            branch_name=branch_name,
            commit_msg=ACTIONS_COMMIT_MESSAGE,
            dry_run=dry_run,
        )
    else:
        _create_branch(
            repository=repository,
            branch_name=branch_name,
            commit_msg=ACTIONS_COMMIT_MESSAGE,
            dry_run=dry_run,
        )
    repository.git.checkout(base)

    open_pulls = github_repository.get_pulls(
        state="open", head=f"{ACTIONS_USER_NAME}/{branch_name}"
    )
    if not list(open_pulls):
        pr_url = _create_pull_request(
            github_repository=github_repository,
            branch_name=branch_name,
            base=base,
            dry_run=dry_run,
        )
    else:
        pr_url = open_pulls[0].url

    return pr_url
