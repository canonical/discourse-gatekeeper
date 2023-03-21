# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling interactions with git repository."""

import base64
import logging
import re
from pathlib import Path

from git import GitCommandError
from git.repo import Repo
from github import Github
from github.GithubException import GithubException
from github.Repository import Repository

from .exceptions import InputError, RepositoryClientError
from .index import DOCUMENTATION_FOLDER_NAME

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
        """Create new branch with existing changes using the default branch as the base.

        Args:
            branch_name: New branch name.
            commit_msg: Commit message for current changes.

        Raises:
            RepositoryClientError: if unexpected error occurred during git operation.
        """
        default_branch = self._github_repo.default_branch
        try:
            self._git_repo.git.fetch("origin", default_branch)
            self._git_repo.git.checkout(default_branch, "--")
            self._git_repo.git.checkout("-b", branch_name)
            self._git_repo.git.add("-A", DOCUMENTATION_FOLDER_NAME)
            self._git_repo.git.commit("-m", f"'{commit_msg}'")
            self._git_repo.git.push("-u", "origin", branch_name)
        except GitCommandError as exc:
            raise RepositoryClientError(f"Unexpected error creating new branch. {exc=!r}") from exc

    def create_pull_request(self, branch_name: str) -> str:
        """Create a pull request from given branch to the default branch.

        Args:
            branch_name: Branch name from which the pull request will be created.

        Raises:
            RepositoryClientError: if unexpected error occurred during git operation.

        Returns:
            The web url to pull request page.
        """
        try:
            pull_request = self._github_repo.create_pull(
                title=ACTIONS_PULL_REQUEST_TITLE,
                body=ACTIONS_PULL_REQUEST_BODY,
                base=self._github_repo.default_branch,
                head=branch_name,
            )
        except GithubException as exc:
            raise RepositoryClientError(
                f"Unexpected error creating pull request. {exc=!r}"
            ) from exc

        return pull_request.html_url

    def is_dirty(self) -> bool:
        """Check if repository path has any changes including new files.

        Returns:
            True if any changes have occurred.
        """
        return self._git_repo.is_dirty(untracked_files=True)

    def get_file_content(self, path: str) -> str:
        """Get the content of a file from the default branch.

        Args:
            path: The path to the file.

        Returns:
            The content of the file on the default branch.

        Raises:
            RepositoryClientError: if there is a problem with communicating with
                GitHub, more than one file is returned or a non-file is returned
                for the provided path.
        """
        try:
            content_file = self._github_repo.get_contents(path)
        except GithubException as exc:
            raise RepositoryClientError(
                f"Could not retrieve the file at {path=}. {exc=!r}"
            ) from exc

        if isinstance(content_file, list):
            raise RepositoryClientError(f"Path matched more than one file {path=}.")

        if content_file.content is None:
            raise RepositoryClientError(f"Path did not match a file {path=}.")

        return base64.b64decode(content_file.content).decode("utf-8")


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
    logging.info("executing in git repository in the directory: %s", local_repo.working_dir)
    github_client = Github(login_or_token=access_token)
    remote_url = local_repo.remote().url
    repository_fullname = _get_repository_name_from_git_url(remote_url=remote_url)
    remote_repo = github_client.get_repo(repository_fullname)
    return RepositoryClient(repository=local_repo, github_repository=remote_repo)
