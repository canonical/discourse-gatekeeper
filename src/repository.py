# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for handling interactions with git repository."""

import base64
import logging
import re
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from functools import cached_property
from itertools import chain
from pathlib import Path
from typing import Any, NamedTuple, cast

from git import GitCommandError
from git.diff import Diff
from git.repo import Repo
from github import Github
from github.Auth import Token
from github.GithubException import GithubException, UnknownObjectException
from github.InputGitTreeElement import InputGitTreeElement
from github.PullRequest import PullRequest
from github.Repository import Repository

from src import commit as commit_module
from src.constants import DOCUMENTATION_FOLDER_NAME
from src.docs_directory import has_docs_directory
from src.exceptions import (
    InputError,
    RepositoryClientError,
    RepositoryFileNotFoundError,
    RepositoryTagNotFoundError,
)
from src.metadata import get as get_metadata
from src.types_ import Metadata

GITHUB_HOSTNAME = "github.com"
ORIGIN_NAME = "origin"
HTTPS_URL_PATTERN = re.compile(rf"^https?:\/\/.*@?{GITHUB_HOSTNAME}\/(.+\/.+?)(.git)?$")
ACTIONS_USER_NAME = "discourse-gatekeeper-docs-bot"
ACTIONS_USER_EMAIL = "discourse-gatekeeper-bot@users.noreply.github.com"
ACTIONS_PULL_REQUEST_TITLE = "[discourse-gatekeeper] Migrate charm docs"
ACTIONS_PULL_REQUEST_BODY = (
    "This pull request was autogenerated by discourse-gatekeeper to migrate "
    "existing documentation from server to the git repository."
)
PR_LINK_NO_CHANGE = "<not created due to no changes in repository>"
TAG_MESSAGE = (
    "tag created by discourse-gatekeeper to mark the latest push to discourse, managed by "
    "discourse-gatekeeper, changes or removal of this tag may lead to unexpected behaviour"
)

CONFIG_USER_SECTION_NAME = "user"
CONFIG_USER_NAME = (CONFIG_USER_SECTION_NAME, "name")
CONFIG_USER_EMAIL = (CONFIG_USER_SECTION_NAME, "email")

BRANCH_PREFIX = "discourse-gatekeeper"
DEFAULT_BRANCH_NAME = f"{BRANCH_PREFIX}/migrate"
ACTIONS_COMMIT_MESSAGE = "migrate docs from server"


class DiffSummary(NamedTuple):
    """Class representing the summary of the dirty status of a repository.

    Attrs:
        is_dirty: boolean indicated whether there is any delta
        new: list of files added in the delta
        removed: list of files removed in the delta
        modified: list of files modified in the delta
    """

    is_dirty: bool
    new: frozenset[str]
    removed: frozenset[str]
    modified: frozenset[str]

    @classmethod
    def from_raw_diff(cls, diffs: Sequence[Diff]) -> "DiffSummary":
        """Return a DiffSummary class from a sequence of git.Diff objects.

        Args:
            diffs: list of git.Diff objects representing the delta between two snapshots.

        Returns:
            DiffSummary class
        """
        new_files = {diff.a_path for diff in diffs if diff.new_file and diff.a_path}
        removed_files = {diff.a_path for diff in diffs if diff.deleted_file and diff.a_path}
        modified_files = {
            diff.a_path
            for diff in diffs
            if diff.renamed_file or diff.change_type == "M"
            if diff.a_path
        }

        return DiffSummary(
            is_dirty=len(diffs) > 0,
            new=frozenset(new_files),
            removed=frozenset(removed_files),
            modified=frozenset(modified_files),
        )

    def __add__(self, other: Any) -> "DiffSummary":
        """Add two instances of DiffSummary classes.

        Args:
            other: DiffSummary object to be added

        Raises:
            ValueError: when the other parameter is not a DiffSummary object

        Returns:
            merged DiffSummary class
        """
        if not isinstance(other, DiffSummary):
            raise ValueError("add operation is only implemented for DiffSummary classes")

        return DiffSummary(
            is_dirty=self.is_dirty or other.is_dirty,
            new=frozenset(self.new).union(other.new),
            removed=frozenset(self.removed).union(other.removed),
            modified=frozenset(self.modified).union(other.modified),
        )

    def __str__(self) -> str:
        """Return string representation of the differences.

        Returns:
            string representing the new, modified and removed files
        """
        modified_str = (f"modified: {','.join(self.modified)}",) if len(self.modified) > 0 else ()
        new_str = (f"new: {','.join(self.new)}",) if len(self.new) > 0 else ()
        removed_str = (f"removed: {','.join(self.removed)}",) if len(self.removed) > 0 else ()
        return " // ".join(chain(modified_str, new_str, removed_str))


def _commit_file_to_tree_element(commit_file: commit_module.FileAction) -> InputGitTreeElement:
    """Convert a file with an action to a tree element.

    Args:
        commit_file: The file action to convert.

    Returns:
        The git tree element.

    Raises:
        NotImplementedError: for unsupported commit file types.
    """
    match type(commit_file):
        case commit_module.FileAddedOrModified:
            commit_file = cast(commit_module.FileAddedOrModified, commit_file)
            return InputGitTreeElement(
                path=str(commit_file.path), mode="100644", type="blob", content=commit_file.content
            )
        case commit_module.FileDeleted:
            commit_file = cast(commit_module.FileDeleted, commit_file)
            return InputGitTreeElement(
                path=str(commit_file.path), mode="100644", type="blob", sha=None
            )
        # Here just in case, should not occur in production
        case _:  # pragma: no cover
            raise NotImplementedError(f"unsupported file in commit, {commit_file}")


class Client:  # pylint: disable=too-many-public-methods
    """Wrapper for git/git-server related functionalities.

    Attrs:
        base_path: The root directory of the repository.
        metadata: Metadata object of the charm
        has_docs_directory: whether the repository has a docs directory
        current_branch: current git branch used in the repository
        current_commit: current commit checkout in the repository
        branches: list of all branches
    """

    def __init__(self, repository: Repo, github_repository: Repository) -> None:
        """Construct.

        Args:
            repository: Client for interacting with local git repository.
            github_repository: Client for interacting with remote github repository.
        """
        self._git_repo = repository
        self._github_repo = github_repository
        self._configure_git_user()

    @cached_property
    def base_path(self) -> Path:
        """Return the Path of the repository.

        Returns:
            Path of the repository.
        """
        return Path(self._git_repo.working_tree_dir or self._git_repo.common_dir)

    @property
    def metadata(self) -> Metadata:
        """Return the Metadata object of the charm."""
        return get_metadata(self.base_path)

    @property
    def has_docs_directory(self) -> bool:
        """Return whether the repository has a docs directory."""
        return has_docs_directory(self.base_path)

    @property
    def current_branch(self) -> str:
        """Return the current branch."""
        try:
            return self._git_repo.active_branch.name
        except TypeError:
            tag = next(
                (tag for tag in self._git_repo.tags if tag.commit == self._git_repo.head.commit),
                None,
            )
            if tag:
                return tag.name
            return self.current_commit

    @property
    def current_commit(self) -> str:
        """Return the current branch."""
        return self._git_repo.head.commit.hexsha

    @property
    def branches(self) -> set[str]:
        """Return all local branches."""
        return {branch.name for branch in self._git_repo.heads}

    @contextmanager
    def with_branch(self, branch_name: str) -> Iterator["Client"]:
        """Return a context for operating within the given branch.

        At the end of the 'with' block, the branch is switched back to what it was initially.

        Args:
            branch_name: name of the branch

        Yields:
            Context to operate on the provided branch
        """
        current_branch = self.current_branch

        try:
            print("before switch")
            result = self.switch(branch_name)
            print("after switch")

            yield result
        finally:
            self.switch(current_branch)

    def get_summary(self, directory: str | None = DOCUMENTATION_FOLDER_NAME) -> DiffSummary:
        """Return a summary of the differences against the most recent commit.

        Args:
            directory: constraint committed changes to a particular folder only. If None, all the
                folders are committed. Default is the documentation folder.

        Returns:
            DiffSummary object representing the summary of the differences.
        """
        self._git_repo.git.add(directory or ".")

        return DiffSummary.from_raw_diff(
            self._git_repo.index.diff(None)
        ) + DiffSummary.from_raw_diff(self._git_repo.head.commit.diff())

    def is_commit_in_branch(self, commit_sha: str, branch: str | None = None) -> bool:
        """Check if commit exists in a given branch.

        Args:
            commit_sha: SHA of the commit to be searched for
            branch: name of the branch against which the check is done. When None, the current
                branch is used.

        Raises:
            RepositoryClientError: when the commit is not found in the repository

        Returns:
             boolean representing whether the commit exists in the branch
        """
        star_pattern = re.compile(r"^\* ")
        try:
            # This effectively means preventing a shallow repository to not behave correctly.
            # Note that the special depth 2147483647 (or 0x7fffffff, the largest positive number a
            # signed 32-bit integer can contain) means infinite depth.
            # Reference: https://git-scm.com/docs/shallow
            self._git_repo.git.fetch("--depth=2147483647")
            branches_with_commit = {
                star_pattern.sub("", _branch).strip()
                for _branch in self._git_repo.git.branch("--contains", commit_sha).split("\n")
            }
        except GitCommandError as exc:
            if f"no such commit {commit_sha}" in exc.stderr:
                raise RepositoryClientError(f"{commit_sha} not found in git repository.") from exc
            raise RepositoryClientError(f"unknown error {exc}") from exc
        return (branch or self.current_branch) in branches_with_commit

    def pull(self, branch_name: str | None = None) -> None:
        """Pull content from remote for the provided branch.

        Args:
            branch_name: branch to be pulled from the remote
        """
        if branch_name is None:
            self._git_repo.git.pull()
        else:
            with self.with_branch(branch_name) as repo:
                repo.pull()

    def switch(self, branch_name: str) -> "Client":
        """Switch branch for the repository.

        Args:
            branch_name: name of the branch to switch to.

        Returns:
            Repository object with the branch switched.
        """
        is_dirty = self.is_dirty()

        print(f"325 {self.get_summary()=}")

        if is_dirty:
            self._git_repo.git.add(".")
            self._git_repo.git.stash()

        print(f"331 {self.get_summary()=}")

        try:
            print(f"334 {self.get_summary()=}")
            self._git_repo.git.fetch("--all")
            print(f"336 {self.get_summary()=}")
            self._git_repo.git.checkout(branch_name, "--")
        finally:
            if is_dirty:
                self._safe_pop_stash(branch_name)
                print(f"341 {self.get_summary()=}")
                self._git_repo.git.reset()
                print(f"343 {self.get_summary()=}")
        print(f"344 {self.get_summary()=}")
        return self

    def _safe_pop_stash(self, branch_name: str) -> None:
        """Pop stashed changes for given branch.

        Args:
            branch_name: name of the branch

        Raises:
            RepositoryClientError: if the pop encounter a critical error.
        """
        try:
            self._git_repo.git.stash("pop")
        except GitCommandError as exc:
            if "CONFLICT" in exc.stdout:
                logging.warning(
                    "There were some conflicts when popping stashes on branch %s. "
                    "Using stashed version.",
                    branch_name,
                )
                self._git_repo.git.checkout("--theirs", DOCUMENTATION_FOLDER_NAME)
            else:
                raise RepositoryClientError(
                    f"Unexpected error when switching branch to {branch_name}. {exc=!r}"
                ) from exc

    def create_branch(self, branch_name: str, base: str | None = None) -> "Client":
        """Create a new branch.

        Note that this will not switch branch. To create and switch branch, please pipe the two
        operations together:

        repository.create_branch(branch_name).switch(branch_name)

        Args:
            branch_name: name of the branch to be created
            base: branch or tag to be branched from

        Raises:
            RepositoryClientError: if an error occur when creating a new branch

        Returns:
            Repository client object.
        """
        try:
            if branch_name in self.branches:
                self._git_repo.git.branch("-D", branch_name)
            self._git_repo.git.branch(branch_name, base or self.current_branch)
        except GitCommandError as exc:
            raise RepositoryClientError(f"Unexpected error creating new branch. {exc=!r}") from exc

        return self

    def _github_client_push(
        self, commit_files: Iterable[commit_module.FileAction], commit_msg: str
    ) -> None:
        """Push files from a commit to GitHub using PyGithub.

        Args:
            commit_files: The files that were added, modified or deleted in a commit.
            commit_msg: The message to use for commits.
        """
        branch = self._github_repo.get_branch(self.current_branch)
        current_tree = self._github_repo.get_git_tree(sha=branch.commit.sha)
        tree_elements = [_commit_file_to_tree_element(commit_file) for commit_file in commit_files]
        tree = self._github_repo.create_git_tree(tree_elements, current_tree)
        commit = self._github_repo.create_git_commit(
            message=commit_msg, tree=tree, parents=[branch.commit.commit]
        )
        branch_git_ref = self._github_repo.get_git_ref(f"heads/{self.current_branch}")
        branch_git_ref.edit(sha=commit.sha)

    def update_branch(
        self,
        commit_msg: str,
        push: bool = True,
        force: bool = False,
        directory: str | None = DOCUMENTATION_FOLDER_NAME,
    ) -> "Client":
        """Update branch with a new commit.

        Args:
            commit_msg: commit message to be committed to the branch
            push: push new changes to remote branches
            force: when pushing to remove, use force flag
            directory: constraint committed changes to a particular folder only. If None, all the
                folders are committed. Default is the documentation folder.

        Raises:
            RepositoryClientError: if any error are encountered in the update process

        Returns:
            Repository client with the updated branch
        """
        push_args = ["-u"]
        if force:
            push_args.append("-f")
        push_args.extend([ORIGIN_NAME, self.current_branch])

        try:
            # Create the branch if it doesn't exist
            if push:
                self._git_repo.git.push(*push_args)

            self._git_repo.git.add("-A", directory or ".")
            self._git_repo.git.commit("-m", f"'{commit_msg}'")
            if push:
                try:
                    self._git_repo.git.push(*push_args)
                except GitCommandError as exc:
                    # Try with the PyGithub client, suppress any errors and report the original
                    # problem on failure
                    try:
                        logging.info(
                            "encountered error with push, try to use GitHub API to sign commits"
                        )
                        show_output = self._git_repo.git.show("--name-status")
                        commit_files = commit_module.parse_git_show(
                            output=show_output, repository_path=self.base_path
                        )
                        self._github_client_push(commit_files=commit_files, commit_msg=commit_msg)
                    except (GitCommandError, GithubException) as nested_exc:
                        # Raise original exception, flake8-docstrings-complete confuses this with a
                        # specific exception rather than re-raising
                        raise exc from nested_exc  # noqa: DCO053
        except GitCommandError as exc:
            raise RepositoryClientError(
                f"Unexpected error updating branch {self.current_branch}. {exc=!r}"
            ) from exc
        return self

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

    def is_same_commit(self, tag: str, commit: str) -> bool:
        """Return whether tag and commit coincides.

        Args:
            tag: name of the tag
            commit: sha of the commit

        Returns:
            True if the two pointers coincides, False otherwise.
        """
        if self.tag_exists(tag):
            with self.with_branch(tag) as repo:
                return repo.current_commit == commit
        return False

    def get_pull_request(self, branch_name: str) -> PullRequest | None:
        """Return open pull request matching the provided branch name.

        Args:
            branch_name: branch name to select open pull requests.

        Raises:
            RepositoryClientError: if more than one PR is open with the given branch name

        Returns:
            PullRequest object. If no PR is found, None is returned.
        """
        open_pull = [
            pull
            for pull in self._github_repo.get_pulls(head=branch_name)
            if pull.head.ref == branch_name
        ]
        if len(open_pull) > 1:
            raise RepositoryClientError(
                f"More than one open pull request with branch {branch_name}"
            )
        if not open_pull:
            return None

        return open_pull[0]

    def create_pull_request(self, base: str) -> PullRequest:
        """Create pull request for changes in given repository path.

        Args:
            base: tag or branch against to which the PR is opened

        Raises:
            InputError: when the repository is not dirty, hence resulting on an empty pull-request

        Returns:
            Pull request object
        """
        if not self.is_dirty(base):
            raise InputError("No files seem to be migrated. Please add contents upstream first.")

        with self.create_branch(DEFAULT_BRANCH_NAME, base).with_branch(
            DEFAULT_BRANCH_NAME
        ) as repo:
            msg = str(repo.get_summary())
            logging.info("Creating new branch with new commit: %s", msg)
            repo.update_branch(msg, force=True)
            pull_request = _create_github_pull_request(
                self._github_repo, DEFAULT_BRANCH_NAME, base
            )
            logging.info("Opening new PR with community contribution: %s", pull_request.html_url)

        return pull_request

    def update_pull_request(self, branch: str) -> None:
        """Update and push changes to the given branch.

        Args:
            branch: name of the branch to be updated
        """
        with self.with_branch(branch) as repo:
            if repo.is_dirty():
                repo.pull()
                msg = str(repo.get_summary())
                logging.info("Summary: %s", msg)
                logging.info("Updating PR with new commit: %s", msg)
                repo.update_branch(msg)

    def is_dirty(self, branch_name: str | None = None) -> bool:
        """Check if repository path has any changes including new files.

        Args:
            branch_name: name of the branch to be checked against dirtiness

        Returns:
            True if any changes have occurred.
        """
        if branch_name is None:
            return self._git_repo.is_dirty(untracked_files=True)

        with self.with_branch(branch_name) as client:
            return client.is_dirty()

    def tag_exists(self, tag_name: str) -> str | None:
        """Check if a given tag exists.

        Args:
            tag_name: name of the tag to be checked for existence

        Returns:
            hash of the commit the tag refers to.
        """
        self._git_repo.git.fetch("--all", "--tags", "--force")
        tags = [tag.commit for tag in self._git_repo.tags if tag_name == tag.name]
        if not tags:
            return None
        return tags[0].hexsha

    def tag_commit(self, tag_name: str, commit_sha: str) -> None:
        """Tag a commit, if the tag already exists, it is deleted first.

        Args:
            tag_name: The name of the tag.
            commit_sha: The SHA of the commit to tag.

        Raises:
            RepositoryClientError: if there is a problem with communicating with GitHub
        """
        try:
            if self.tag_exists(tag_name):
                logging.info("Removing tag %s", tag_name)
                self._git_repo.git.tag("-d", tag_name)
                self._git_repo.git.push("--delete", "origin", tag_name)

            logging.info("Tagging commit %s with tag %s", commit_sha, tag_name)
            self._git_repo.git.tag(tag_name, commit_sha)
            self._git_repo.git.push("origin", tag_name)

        except GitCommandError as exc:
            logging.error("Tagging commit failed because of %s", exc)
            raise RepositoryClientError(f"Tagging commit failed. {exc=!r}") from exc

    def get_file_content_from_tag(self, path: str, tag_name: str) -> str:
        """Get the content of a file for a specific tag.

        Args:
            path: The path to the file.
            tag_name: The name of the tag.

        Returns:
            The content of the file for the tag.

        Raises:
            RepositoryTagNotFoundError: if the tag could not be found in the repository.
            RepositoryFileNotFoundError: if the file could not be retrieved from GitHub, more than
                one file is returned or a non-file is returned
            RepositoryClientError: if there is a problem with communicating with GitHub
        """
        # Get the tag
        try:
            tag_ref = self._github_repo.get_git_ref(f"tags/{tag_name}")
            # git has 2 types of tags, lightweight and annotated tags:
            # https://git-scm.com/book/en/v2/Git-Basics-Tagging
            if tag_ref.object.type == "commit":
                # lightweight tag, the SHA of the tag is the commit SHA
                commit_sha = tag_ref.object.sha
            else:
                # annotated tag, need to retrieve the commit SHA linked to the tag
                git_tag = self._github_repo.get_git_tag(tag_ref.object.sha)
                commit_sha = git_tag.object.sha
        except UnknownObjectException as exc:
            raise RepositoryTagNotFoundError(
                f"Could not retrieve the tag {tag_name=}. {exc=!r}"
            ) from exc
        except GithubException as exc:
            raise RepositoryClientError(f"Communication with GitHub failed. {exc=!r}") from exc

        # Get the file contents
        try:
            content_file = self._github_repo.get_contents(path, commit_sha)
        except UnknownObjectException as exc:
            raise RepositoryFileNotFoundError(
                f"Could not retrieve the file at {path=} for tag {tag_name}. {exc=!r}"
            ) from exc
        except GithubException as exc:
            raise RepositoryClientError(f"Communication with GitHub failed. {exc=!r}") from exc

        if isinstance(content_file, list):
            raise RepositoryFileNotFoundError(
                f"Path matched more than one file {path=} for tag {tag_name}."
            )

        if content_file.content is None:
            raise RepositoryFileNotFoundError(
                f"Path did not match a file {path=} for tag {tag_name}."
            )

        return base64.b64decode(content_file.content).decode("utf-8")


def _create_github_pull_request(
    github_repo: Repository, branch_name: str, base: str
) -> PullRequest:
    """Create pull request using the provided branch.

    Args:
        github_repo: Github repository where to open pull request.
        branch_name: name of the branch used to open the pull request.
        base: name of the base branch which the PR needs to be opened against

    Raises:
        RepositoryClientError: if any error are encountered when creating the pull request.

    Returns:
        PullRequest object representing the opened pull request.
    """
    try:
        pull_request = github_repo.create_pull(
            title=ACTIONS_PULL_REQUEST_TITLE,
            body=ACTIONS_PULL_REQUEST_BODY,
            base=base,
            head=branch_name,
        )
    except GithubException as exc:
        raise RepositoryClientError(f"Unexpected error creating pull request. {exc=!r}") from exc

    return pull_request


def _get_repository_name_from_git_url(remote_url: str) -> str:
    """Get repository name from git remote URL.

    Args:
        remote_url: URL of remote repository.
        e.g. https://github.com/canonical/discourse-gatekeeper.git

    Raises:
        InputError: if invalid repository url was given.

    Returns:
        Git repository name. e.g. canonical/discourse-gatekeeper.
    """
    matched_repository = HTTPS_URL_PATTERN.match(remote_url)
    if not matched_repository:
        raise InputError(f"Invalid remote repository url {remote_url=!r}")
    return matched_repository.group(1)


def create_repository_client(access_token: str | None, base_path: Path) -> Client:
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
    github_client = Github(auth=Token(access_token))
    remote_url = local_repo.remote().url
    repository_fullname = _get_repository_name_from_git_url(remote_url=remote_url)
    remote_repo = github_client.get_repo(repository_fullname)
    return Client(repository=local_repo, github_repository=remote_repo)
