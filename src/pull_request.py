# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling interactions with git repository."""

import logging

from .exceptions import InputError
from .repository import Client as RepositoryClient

BRANCH_PREFIX = "upload-charm-docs"
DEFAULT_BRANCH_NAME = f"{BRANCH_PREFIX}/migrate"
ACTIONS_COMMIT_MESSAGE = "migrate docs from server"

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

    def update_branch(self, commit_msg: str):
        ...

    def create_branch(self, branch_name: str) -> None:
        """Create new branch with existing changes using the default branch as the base.

        Args:
            branch_name: New branch name.
            commit_msg: Commit message for current changes.

        Raises:
            RepositoryClientError: if unexpected error occurred during git operation.
        """
        default_branch = self._github_repo.default_branch
        try:

            # What about dividing the logic between creating and updating the branch?

            self._git_repo.git.fetch("origin", default_branch)
            self._git_repo.git.checkout(default_branch, "--")
            self._git_repo.git.checkout("-b", branch_name)
            self._git_repo.git.add("-A", DOCUMENTATION_FOLDER_NAME)
            self._git_repo.git.commit("-m", f"'{commit_msg}'")
            self._git_repo.git.push("-u", "origin", branch_name)
        except GitCommandError as exc:
            raise RepositoryClientError(f"Unexpected error creating new branch. {exc=!r}") from exc

    def get_or_create_pull_request(self, branch_name: str) -> str:
        """Create a pull request from given branch to the default branch.

        Args:
            branch_name: Branch name from which the pull request will be created.

        Raises:
            RepositoryClientError: if unexpected error occurred during git operation.

        Returns:
            The web url to pull request page.
        """
        try:
            open_pull = [
                pull for pull in self._github_repo.get_pulls()
                if pull.head.ref == branch_name
            ]
            if len(open_pull)>1:
                raise ...
            elif len(open_pull)==1:
                return open_pull[0]

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

    def is_dirty(self, branch: Optional[str]=None) -> bool:
        """Check if repository path has any changes including new files.

        Returns:
            True if any changes have occurred.
        """

        # handle the errors and nice2have use context

        return self._git_repo.is_dirty(untracked_files=True)


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
