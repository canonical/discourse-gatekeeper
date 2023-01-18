# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling interactions with git repository."""

import logging
import re
from contextlib import suppress
from pathlib import Path

from git import GitCommandError
from git.repo import Repo
from github import Github
from github.GithubException import GithubException
from github.Repository import Repository

from .exceptions import InputError, RepositoryClientError

GITHUB_HOSTNAME = "github.com"
HTTPS_URL_PATTERN = re.compile(rf"^https?:\/\/.*@?{GITHUB_HOSTNAME}\/(.+\/.+?)(.git)?$")
ACTIONS_USER_NAME = "upload-charms-docs-bot"
ACTIONS_USER_EMAIL = "upload-charms-docs-bot@users.noreply.github.com"
ACTIONS_COMMIT_MESSAGE = "migrate docs from server"
ACTIONS_PULL_REQUEST_TITLE = "[upload-charm-docs] Migrate charm docs"
ACTIONS_PULL_REQUEST_BODY = (
    "This pull request was autogenerated by upload-charm-docs to migrate "
    "existing documentation from server to the git repository."
)
PR_LINK_NO_CHANGE = "<not created due to no changes in repository>"
BRANCH_PREFIX = "upload-charm-docs"
DEFAULT_BRANCH_NAME = f"{BRANCH_PREFIX}/migrate"

CONFIG_USER_SECTION_NAME = "user"
CONFIG_USER_NAME = (CONFIG_USER_SECTION_NAME, "name")
CONFIG_USER_EMAIL = (CONFIG_USER_SECTION_NAME, "email")


class RepositoryClient:
    """Wrapper for git/git-server related functionalities."""

    def __init__(self, repository: Repo, github_repository: Repository) -> None:
        """Construct.

        Args:
            repository: Client for interacting with local git repository.
            github_repository: Client for interacting with remote github repository.
        """
        self._git_repo = repository
        self._github_repo = github_repository
        self._configure_git_user()

    def _configure_git_user(self) -> None:
        """Configure action git profile defaults.

        Configured profile appears as the git committer.
        """
        config_reader = self._git_repo.config_reader(config_level="repository")
        with self._git_repo.config_writer(config_level="repository") as config_writer:
            if not config_reader.has_section(
                CONFIG_USER_SECTION_NAME
            ) or not config_reader.get_value(*CONFIG_USER_NAME):
                config_writer.set_value(*CONFIG_USER_NAME, ACTIONS_USER_NAME)
            if not config_reader.has_section(
                CONFIG_USER_SECTION_NAME
            ) or not config_reader.get_value(*CONFIG_USER_EMAIL):
                config_writer.set_value(*CONFIG_USER_EMAIL, ACTIONS_USER_EMAIL)

    def check_branch_exists(self, branch_name: str) -> bool:
        """Check if branch exists on remote.

        Args:
            branch_name: Branch name to check on remote.

        Raises:
            RepositoryClientError: if unexpected error occurred during git operation.

        Returns:
            True if branch already exists, False otherwise.
        """
        try:
            self._git_repo.git.fetch("origin", branch_name)
            return True
        except GitCommandError as exc:
            if "couldn't find remote ref" in exc.stderr:
                return False
            raise RepositoryClientError(
                f"Unexpected error checking existing branch. {exc=!r}"
            ) from exc

    def create_branch(self, branch_name: str, commit_msg: str) -> None:
        """Create new branch with existing changes.

        Args:
            branch_name: New branch name.
            commit_msg: Commit message for current changes.

        Raises:
            RepositoryClientError: if unexpected error occurred during git operation.
        """
        try:
            self._git_repo.git.checkout("-b", branch_name)
            self._git_repo.git.add(".")
            self._git_repo.git.commit("-m", f"'{commit_msg}'")
            self._git_repo.git.push("-u", "origin", branch_name)
        except GitCommandError as exc:
            raise RepositoryClientError(f"Unexpected error creating new branch. {exc=!r}") from exc

    def create_pull_request(self, branch_name: str, base: str) -> str:
        """Create a pull request from given branch to base.

        Args:
            branch_name: Branch name from which the pull request will be created.
            base: Base branch to which the pull request will be created.

        Raises:
            RepositoryClientError: if unexpected error occurred during git operation.

        Returns:
            The web url to pull request page.
        """
        try:
            pull_request = self._github_repo.create_pull(
                title=ACTIONS_PULL_REQUEST_TITLE,
                body=ACTIONS_PULL_REQUEST_BODY,
                base=base,
                head=branch_name,
            )
        except GithubException as exc:
            raise RepositoryClientError(
                f"Unexpected error creating pull request. {exc=!r}"
            ) from exc

        return pull_request.html_url

    # This is only needed for e2e tests
    def cleanup_migration(self) -> None:  # pragma: nocover
        """Delete the pull request and branch created for the migration."""
        for pull_request in self._github_repo.get_pulls():
            if pull_request.title == ACTIONS_PULL_REQUEST_TITLE:
                pull_request.edit(state="closed")
        with suppress(GithubException):
            self._github_repo.get_git_ref(f"heads/{DEFAULT_BRANCH_NAME}").delete()

    def is_dirty(self) -> bool:
        """Check if repository path has any changes including new files.

        Returns:
            True if any changes have occurred.
        """
        return self._git_repo.is_dirty(untracked_files=True)

    def detach_head(self) -> None:
        """Detach from the current branch to ensure no further commits can occur."""
        self._git_repo.head.set_reference(self._git_repo.head.commit.hexsha)
        self._git_repo.git.checkout(self._git_repo.head.commit.hexsha)


def create_pull_request(repository: RepositoryClient, current_branch_name: str) -> str:
    """Create pull request for changes in given repository path.

    Args:
        repository: A git client to interact with local and remote git repository.
        current_branch_name: The name of the branch the migration is running on.

    Raises:
        InputError: if pull request branch name is invalid or the a branch
        with same name already exists.

    Returns:
        Pull request URL string. None if no pull request was created/modified.
    """
    if current_branch_name == DEFAULT_BRANCH_NAME:
        raise InputError(
            f"Pull request branch cannot be named {DEFAULT_BRANCH_NAME}."
            f"Branch name {DEFAULT_BRANCH_NAME} is reserved for creating a migration branch."
            "Please try again after changing the branch name."
        )
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
    pull_request_web_link = repository.create_pull_request(
        branch_name=DEFAULT_BRANCH_NAME,
        base=current_branch_name,
    )

    # Detach head to ensure no further changes can be made
    repository.detach_head()

    return pull_request_web_link


def _get_repository_name_from_git_url(remote_url: str) -> str:
    """Get repository name from git remote URL.

    Args:
        remote_url: URL of remote repository.
        e.g. https://github.com/canonical/upload-charm-docs.git

    Raises:
        InputError: if invalid repository url was given.

    Returns:
        Git repository name. e.g. canonical/upload-charm-docs.
    """
    matched_repository = HTTPS_URL_PATTERN.match(remote_url)
    if not matched_repository:
        raise InputError(f"Invalid remote repository url {remote_url=!r}")
    return matched_repository.group(1)


def create_repository_client(access_token: str | None, base_path: Path) -> RepositoryClient:
    """Create a Github instance to handle communication with Github server.

    Args:
        access_token: Access token that has permissions to open a pull request.
        base_path: Path where local .git resides in.

    Raises:
        InputError: if invalid access token or invalid git remote URL is provided.

    Returns:
        A Github repository instance.
    """
    if not access_token:
        raise InputError(
            f"Invalid 'access_token' input, it must be non-empty, got {access_token=!r}"
        )

    local_repo = Repo(base_path)
    github_client = Github(login_or_token=access_token)
    remote_url = local_repo.remote().url
    repository_fullname = _get_repository_name_from_git_url(remote_url=remote_url)
    remote_repo = github_client.get_repo(repository_fullname)
    return RepositoryClient(repository=local_repo, github_repository=remote_repo)
