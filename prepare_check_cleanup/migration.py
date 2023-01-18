# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility for running the migration action, primarily for testing purposes."""

import argparse
import json
import logging
import os
import sys
from contextlib import suppress
from enum import Enum
from pathlib import Path

from github.GithubException import GithubException
from github.GitRef import GitRef
from github.PullRequest import PullRequest
from github.Repository import Repository

from prepare_check_cleanup import exit_
from src.discourse import Discourse, create_discourse
from src.exceptions import DiscourseError
from src.pull_request import (
    ACTIONS_PULL_REQUEST_TITLE,
    DEFAULT_BRANCH_NAME,
    create_repository_client,
)
from src.reconcile import NAVIGATION_TABLE_START


class Action(str, Enum):
    """The actions the utility can take.

    Attrs:
        PREPARE: Prepare discourse pages before running the migration.
        CHECK_BRANCH: Check that the migration branch was created.
        CHECK_PULL_REQUEST: Check that the migration pull request was created.
        CLEANUP: Delete discourse pages before after the migration.
    """

    PREPARE = "prepare"
    CHECK_BRANCH = "check-branch"
    CHECK_PULL_REQUEST = "check-pull-request"
    CLEANUP = "cleanup"


def main() -> None:
    """Execute requested migration action.

    Raises:
        NotImplementedError: if an action was received for which there is no imlpementation.
    """
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        prog="MigrationTestSupport",
        description="Support functions for the migration testing.",
    )
    parser.add_argument(
        "--action", help="Action to run", choices=tuple(action.value for action in Action)
    )
    parser.add_argument(
        "--action-kwargs", help="Arguments for the action as a JSON mapping", default="{}"
    )
    args = parser.parse_args()
    action_kwargs = json.loads(args.action_kwargs)

    match args.action:
        case Action.PREPARE.value:
            prepare(**action_kwargs)
            sys.exit(0)
        case Action.CHECK_BRANCH.value:
            exit_.with_result(check_branch(**action_kwargs))
        case Action.CHECK_PULL_REQUEST.value:
            exit_.with_result(check_pull_request(**action_kwargs))
        case Action.CLEANUP.value:
            cleanup(**action_kwargs)
            sys.exit(0)
        case _:
            raise NotImplementedError(f"{args.action} has not been implemented")


def _create_discourse_client(config: str) -> Discourse:
    """Create an API for interacting with GitHub.

    Args:
        config: The details required for interacting with discourse.

    Returns:
        API to the GitHub repository.
    """
    return create_discourse(**json.loads(config))


def prepare(index_filename: str, page_filename: str, discourse_config: str) -> None:
    """Create the content and index page.

    Args:
        index_filename: The path to the file with the index file contents. The first line will be
            used as the title and the content will be used as the topic content.
        page_filename: The path to the file with the content file contents. The first line will
            be used as the title and the content will be used as the topic content.
        discourse_config: Details required to communicate with discourse.
    """
    discourse = _create_discourse_client(config=discourse_config)

    page_file = Path(page_filename)
    page_content = page_file.read_text(encoding="utf-8")
    page_title = page_content.splitlines()[0].lstrip("# ")
    page_url = discourse.create_topic(title=page_title, content=page_content)

    index_file = Path(index_filename)
    index_content = index_file.read_text(encoding="utf-8")
    index_topic_content = (
        f"{index_content}{NAVIGATION_TABLE_START}\n| 1 | page | [{page_title}]({page_url}) |\n"
    )
    index_title = index_content.splitlines()[0].lstrip("# ")
    index_url = discourse.create_topic(title=index_title, content=index_topic_content)

    topics = {"index": index_url, "page": page_url}

    github_output = os.getenv("GITHUB_OUTPUT")
    assert github_output, (
        "the GITHUB_OUTPUT environment variable is empty or defined, "
        "is this running in a GitHub workflow?"
    )
    output_file = Path(github_output)
    output_file.write_text(f"topics={json.dumps(topics, separators=(',', ':'))}", encoding="utf-8")


def _create_repository_client(github_access_token: str) -> Repository:
    """Create an API for interacting with GitHub.

    Args:
        github_access_token: The secret required for interactions with GitHub.

    Returns:
        API to the GitHub repository.
    """
    repository = create_repository_client(access_token=github_access_token, base_path=Path())
    # Accessing private client since this is for testing pourposes only, otherwise would need to
    # add code to pull_request only needed for testing
    return repository._github_repo  # pylint: disable=protected-access


def _get_migration_pull_request(github_repo: Repository) -> PullRequest | None:
    """Get the migration pull request if it exists.

    Args:
        github_repo: API for interacting with GitHub.

    Returns:
        The migration pull request or None if it doesn't exist.
    """
    return next(
        (
            pull_request
            for pull_request in github_repo.get_pulls()
            if pull_request.title == ACTIONS_PULL_REQUEST_TITLE
        ),
        None,
    )


def _get_migration_branch(github_repo: Repository) -> GitRef | None:
    """Get the migration branch if it exists.

    Args:
        github_repo: API for interacting with GitHub.

    Returns:
        The migration branch or None if it doesn't exist.
    """
    with suppress(GithubException):
        return github_repo.get_git_ref(f"heads/{DEFAULT_BRANCH_NAME}")
    return None


def check_branch(github_access_token: str) -> bool:
    """Check that the migration branch was created.

    Args:
        github_access_token: The secret required for interactions with GitHub.

    Returns:
        Whether the test succeeded.
    """
    test_name = "check-branch"

    github_repo = _create_repository_client(github_access_token=github_access_token)
    migration_branch = _get_migration_branch(github_repo=github_repo)
    if not migration_branch:
        logging.error(
            "%s check failed, migration branch %s not created", test_name, DEFAULT_BRANCH_NAME
        )
        return False

    logging.info("%s check succeeded", test_name)
    return True


def check_pull_request(github_access_token: str) -> bool:
    """Check that the migration pull request was created.

    Args:
        github_access_token: The secret required for interactions with GitHub.

    Returns:
        Whether the test succeeded.
    """
    test_name = "check-pull-request"

    github_repo = _create_repository_client(github_access_token=github_access_token)
    migration_pull_request = _get_migration_pull_request(github_repo=github_repo)
    if not migration_pull_request:
        logging.error(
            "%s check failed, migration pull request %s not created",
            test_name,
            ACTIONS_PULL_REQUEST_TITLE,
        )
        return False

    logging.info("%s check succeeded", test_name)
    return True


def cleanup(topics: dict[str, str], github_access_token: str, discourse_config: str) -> None:
    """Clean up testing artifacts on GitHub and Discourse.

    Args:
        topics: The discourse topics created for the migration.
        github_access_token: The secret required for interactions with GitHub.
        discourse_config: Details required to communicate with discourse.
    """
    # Delete discourse topics
    discourse = _create_discourse_client(config=discourse_config)
    with suppress(DiscourseError):
        for topic_url in topics.values():
            discourse.delete_topic(url=topic_url)

    github_repo = _create_repository_client(github_access_token=github_access_token)
    # Delete the migration PR
    migration_pull_request = _get_migration_pull_request(github_repo=github_repo)
    if migration_pull_request:
        migration_pull_request.edit(state="closed")
    # Delete the migration branch
    migration_branch = _get_migration_branch(github_repo=github_repo)
    if migration_branch:
        with suppress(GithubException):
            migration_branch.delete()


if __name__ == "__main__":
    main()
