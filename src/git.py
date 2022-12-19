# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling git repository."""

import re
from pathlib import Path
from uuid import uuid4

from github import Github

from git.exc import GitCommandError
from git.repo import Repo

from .exceptions import GitError, InputError

GITHUB_HOSTNAME = "github.com"
HTTPS_URL_PATTERN = re.compile(rf"^https?:\/\/.*@?{GITHUB_HOSTNAME}\/(.+\/.+?)(.git)?$")

GITHUB_HOSTNAME = "github.com"
HTTPS_URL_PATTERN = re.compile(rf"^https?:\/\/.*@?{GITHUB_HOSTNAME}\/(.+\/.+?)(.git)?$")


class Git:
    """Client to interact with git repository."""

    user_name = "actions-bot"
    user_email = "actions-bot@users.noreply.github.com"

    def __init__(self, access_token: str, repository_path: Path) -> None:
        """Construct.

        Args:
            access_token: Github access token.
            repository_path: Repository root where .git resides.
        """
        self._repository = Repo(path=repository_path)
        self._github = Github(login_or_token=access_token)
        self._github_repo = self._github.get_repo(
            self._get_repository_name(self._repository.remote().url)
        )
        self._configure_user()

    def _get_repository_name(self, remote_url: str):
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
            raise GitError(f"No match for remote repository name {remote_url=!r}")
        return matched_repository.group(1)

    def _configure_user(self):
        """Configure action git profile defaults."""
        config_writer = self._repository.config_writer()
        config_writer.set_value("user", "name", self.user_name)
        config_writer.set_value("user", "email", self.user_email)
        config_writer.release()

    def _check_branch_exists(self, branch_name: str):
        """Check if branch exists on remote.

        Args:
            branch_name: Branch name to check on remote.

        Returns:
            True if branch already exists, False otherwise.
        """
        try:
            self._repository.git.fetch("origin", branch_name)
            return True
        except GitCommandError as exc:
            if "couldn't find remote ref" in exc.stderr:
                return False
            raise exc

    def _merge_existing_branch(self, branch_name: str, commit_msg: str):
        """Merge existing changes in current repository with specified branch with theirs strategy.

        Args:
            branch_name: Base branch to merge to.
            commit_msg: Commit message for current changes.
        """
        temp_branch = str(uuid4())
        head = self._repository.create_head(temp_branch)
        head.checkout()
        self._repository.git.add(".")
        self._repository.git.commit("-m", commit_msg)

        self._repository.git.checkout(branch_name)
        self._repository.git.pull()
        self._repository.git.merge(temp_branch, "-Xtheirs", "--squash", "--no-edit")
        self._repository.git.commit("-m", commit_msg)
        self._repository.git.push("-u", "origin", branch_name)

        self._repository.git.branch("-D", temp_branch)

    def _create_branch(self, branch_name: str, commit_msg: str):
        """Create new branch with existing changes.

        Args:
            branch_name: New branch name.
            commit_msg: Commit message for current changes.
        """
        self._repository.git.checkout("-b", branch_name)
        self._repository.git.add(".")
        self._repository.git.commit("-m", commit_msg)
        self._repository.git.push("--set-upstream", "origin", branch_name)

    def create_pull_request(
        self,
        title: str,
        body: str,
        branch_name: str,
        commit_msg: str = "actions-bot commit",
    ):
        """Creates pull request or updates pull request if already existing.

        Args:
            title: Pull request title.
            body: Pull request body.
            branch: Branch name to base Pull Request from.
            commit_msg: Commit message to push changes with. Defaults to "actions-bot commit"

        Returns:
            Pull request URL. None if URL is not created or updated.
        """
        base = self._repository.active_branch.name

        if base == branch_name:
            raise InputError("Branch name cannot be equal to base branch.")

        if not self._repository.is_dirty(untracked_files=True):
            return None

        if self._check_branch_exists(branch_name=branch_name):
            self._merge_existing_branch(branch_name=branch_name, commit_msg=commit_msg)
        else:
            self._create_branch(branch_name=branch_name, commit_msg=commit_msg)

        self._repository.git.checkout(base)

        open_pulls = self._github_repo.get_pulls(state="open", head=f"actions-bot/{branch_name}")
        if not list(open_pulls):
            pull_request = self._github_repo.create_pull(
                title=title, body=body, base=base, head=branch_name
            )
        else:
            pull_request = open_pulls[0]

        return pull_request.url


def create_git(access_token: str, repository_path: Path):
    """Create Github client.

    Args:
        access_token: Github access token.
        repository_path: Repository root where .git resides.

    Returns:
        A github client that connected to given repository.

    Raises:
    InputError: if access_token is not string or empty.
    """
    if not isinstance(access_token, str):
        raise InputError(
            f"Invalid 'access_token' input, it must be a string, got {access_token=!r}"
        )
    if not access_token:
        raise InputError(
            f"Invalid 'access_token' input, it must be non-empty, got {access_token=!r}"
        )

    return Git(access_token=access_token, repository_path=repository_path)
