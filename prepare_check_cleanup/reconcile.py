# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility for running the reconcile action, primarily for testing purposes."""

import argparse
import contextlib
import json
import logging
import sys
from enum import StrEnum
from pathlib import Path

from github import Github
from github.GithubException import GithubException, UnknownObjectException

from prepare_check_cleanup import exit_, output
from src.discourse import Discourse, create_discourse
from src.exceptions import DiscourseError
from src.pull_request import BRANCH_PREFIX

_UPDATE_BRANCH = f"{BRANCH_PREFIX}/update-test"


class Action(StrEnum):
    """The actions the utility can take.

    Attrs:
        CHECK_DRAFT: Check that the draft integration test succeeded.
        CHECK_CREATE: Check that the create integration test succeeded.
        PREPARE_UPDATE: Prepare for the update test.
        CHECK_UPDATE: Check that the update integration test succeeded.
        CHECK_DELETE_TOPICS: Check that the delete_topics integration test succeeded.
        CHECK_DELETE: Check that the delete integration test succeeded.
        CLEANUP: Discourse cleanup after the testing.
    """

    CHECK_DRAFT = "check-draft"
    CHECK_CREATE = "check-create"
    PREPARE_UPDATE = "prepare-update"
    CHECK_UPDATE = "check-update"
    CHECK_DELETE_TOPICS = "check-delete-topics"
    CHECK_DELETE = "check-delete"
    CLEANUP = "cleanup"


def main() -> None:
    """Execute requested reconcilliation action.

    Raises:
        NotImplementedError: if an action was received for which there is no imlpementation.
    """
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        prog="ReconcileTestSupport",
        description="Check or delete posts created on discourse during an action execution.",
    )
    parser.add_argument("urls_with_actions", help="The pages that were created during execution")
    parser.add_argument(
        "discourse_config", help="The discourse configuration used to create the pages"
    )
    parser.add_argument(
        "--action", help="Action to run", choices=tuple(action.value for action in Action)
    )
    parser.add_argument(
        "--action-kwargs", help="Arguments for the action as a JSON mapping", default="{}"
    )
    args = parser.parse_args()
    urls_with_actions = json.loads(args.urls_with_actions)
    discourse_config = json.loads(args.discourse_config)
    action_kwargs = json.loads(args.action_kwargs)

    discourse = create_discourse(**discourse_config)

    match args.action:
        case Action.CHECK_DRAFT.value:
            exit_.with_result(check_draft(urls_with_actions=urls_with_actions, **action_kwargs))
        case Action.CHECK_CREATE.value:
            exit_.with_result(
                check_create(
                    urls_with_actions=urls_with_actions, discourse=discourse, **action_kwargs
                )
            )
        case Action.PREPARE_UPDATE.value:
            prepare_update(**action_kwargs)
            sys.exit(0)
        case Action.CHECK_UPDATE.value:
            exit_.with_result(
                check_update(
                    urls_with_actions=urls_with_actions, discourse=discourse, **action_kwargs
                )
            )
        case Action.CHECK_DELETE_TOPICS.value:
            exit_.with_result(
                check_delete_topics(
                    urls_with_actions=urls_with_actions, discourse=discourse, **action_kwargs
                )
            )
        case Action.CHECK_DELETE.value:
            exit_.with_result(
                check_delete(
                    urls_with_actions=urls_with_actions, discourse=discourse, **action_kwargs
                )
            )
        case Action.CLEANUP.value:
            cleanup(urls_with_actions=urls_with_actions, discourse=discourse, **action_kwargs)
            sys.exit(0)
        case _:
            raise NotImplementedError(f"{args.action} has not been implemented")


def _check_url_count(
    urls_with_actions: dict[str, str], expected_count: int, test_name: str
) -> bool:
    """Perform the check for the number of URLs.

    Success is if the number of urls in urls_with_actions matches the expected count.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        expected_count: The expected number of URLs.
        test_name: The name of the test to include in the logging message.

    Returns:
        Whether the test succeeded.
    """
    if (url_count := len(urls_with_actions)) != expected_count:
        logging.error(
            "%s check failed, expected %s URLs with actions, got %s, urls_with_actions=%s",
            test_name,
            expected_count,
            url_count,
            urls_with_actions,
        )
        return False
    return True


def _check_url_retrieve(
    urls_with_actions: dict[str, str], discourse: Discourse, test_name: str
) -> bool:
    """Check that retrieving the URL succeeds.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.
        test_name: The name of the test to include in the logging message.

    Returns:
        Whether the test succeeded.
    """
    for url in urls_with_actions.keys():
        try:
            discourse.retrieve_topic(url=url)
        except DiscourseError as exc:
            logging.error(
                "%s check failed, URL retrieval failed for %s, error: %s, urls_with_actions=%s",
                test_name,
                url,
                exc,
                urls_with_actions,
            )
            return False
    return True


def _check_url_result(
    urls_with_actions: dict[str, str], expected_result: list[str], test_name: str
) -> bool:
    """Check the results for the URLs.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        expected_result: The expected results.
        test_name: The name of the test to include in the logging message.

    Returns:
        Whether the test succeeded.
    """
    if sorted(results := urls_with_actions.values()) != sorted(expected_result):
        logging.error(
            "%s check failed, the result is not as expected, "
            "got: %s, expected: %s, urls_with_actions=%s",
            test_name,
            results,
            expected_result,
            urls_with_actions,
        )
        return False
    return True


def check_draft(urls_with_actions: dict[str, str], expected_url_results: list[str]) -> bool:
    """Check that the draft test succeeded.

    Success is indicated by that there are the expected number of URLs in urls_with_actions.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        expected_url_results: The expected url results.

    Returns:
        Whether the test succeeded.
    """
    test_name = "draft"
    if not _check_url_count(
        urls_with_actions=urls_with_actions,
        expected_count=len(expected_url_results),
        test_name=test_name,
    ):
        return False

    logging.info("%s check succeeded", test_name)
    return True


def check_create(
    urls_with_actions: dict[str, str], discourse: Discourse, expected_url_results: list[str]
) -> bool:
    """Check that the create test succeeded.

    Success is indicated by that there are the expected number of URLs with the expected result and
    that retrieving the URLs succeeds.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.
        expected_url_results: The expected url results.

    Returns:
        Whether the test succeeded.
    """
    test_name = "create"
    if not _check_url_count(
        urls_with_actions=urls_with_actions,
        expected_count=len(expected_url_results),
        test_name=test_name,
    ):
        return False

    if not _check_url_result(
        urls_with_actions=urls_with_actions,
        expected_result=expected_url_results,
        test_name=test_name,
    ):
        return False

    if not _check_url_retrieve(
        urls_with_actions=urls_with_actions, discourse=discourse, test_name=test_name
    ):
        return False

    logging.info("%s check succeeded", test_name)
    return True


def prepare_update(github_token: str, repo: str, filename: str) -> None:
    """Prepare for the update action.

    Create a branch and push a file to that branch.

    Args:
        github_token: Token for communication with GitHub.
        repo: The name of the repository.
        filename: The name of the file to push to the branch.
    """
    github_client = Github(login_or_token=github_token)
    github_repo = github_client.get_repo(repo)
    base = github_repo.get_branch(github_repo.default_branch)
    github_repo.create_git_ref(ref=f"refs/heads/{_UPDATE_BRANCH}", sha=base.commit.sha)

    # Delete the file if it already exists in the branch
    with contextlib.suppress(UnknownObjectException):
        contents = github_repo.get_contents(filename, ref=_UPDATE_BRANCH)
        assert not isinstance(contents, list)
        assert isinstance(contents.path, str)
        github_repo.delete_file(
            contents.path,
            "remove pre-existing file for update test",
            contents.sha,
            branch=_UPDATE_BRANCH,
        )

    # Create the file in the branch
    github_repo.create_file(
        filename,
        "file for update test",
        Path(filename).read_text(encoding="utf-8"),
        branch=_UPDATE_BRANCH,
    )

    output.write(f"update_branch={_UPDATE_BRANCH}\n")


def check_update(
    urls_with_actions: dict[str, str], discourse: Discourse, expected_url_results: list[str]
) -> bool:
    """Check that the update test succeeded.

    Success is indicated by that there are the expected number of URLs with the expected result and
    that retrieving the URLs succeeds.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.
        expected_url_results: The expected url results.

    Returns:
        Whether the test succeeded.
    """
    test_name = "update"
    if not _check_url_count(
        urls_with_actions=urls_with_actions,
        expected_count=len(expected_url_results),
        test_name=test_name,
    ):
        return False

    if not _check_url_result(
        urls_with_actions=urls_with_actions,
        expected_result=expected_url_results,
        test_name=test_name,
    ):
        return False

    if not _check_url_retrieve(
        urls_with_actions=urls_with_actions, discourse=discourse, test_name=test_name
    ):
        return False

    logging.info("%s check succeeded", test_name)
    return True


def check_delete_topics(
    urls_with_actions: dict[str, str], discourse: Discourse, expected_url_results: list[str]
) -> bool:
    """Check that the delete_topics test succeeded.

    Success is indicated by that there are the expected number of URLs and results in
    urls_with_actions and that retrieving the URLs succeeds (none have been deleted).

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.
        expected_url_results: The expected url results.

    Returns:
        Whether the test succeeded.
    """
    test_name = "delete_topics"
    if not _check_url_count(
        urls_with_actions=urls_with_actions,
        expected_count=len(expected_url_results),
        test_name=test_name,
    ):
        return False

    if not _check_url_result(
        urls_with_actions=urls_with_actions,
        expected_result=expected_url_results,
        test_name=test_name,
    ):
        return False

    if not _check_url_retrieve(
        urls_with_actions=urls_with_actions, discourse=discourse, test_name=test_name
    ):
        return False

    logging.info("%s check succeeded", test_name)
    return True


def check_delete(
    urls_with_actions: dict[str, str], discourse: Discourse, expected_url_results: list[str]
) -> bool:
    """Check that the delete test succeeded.

    Success is indicated by that there are the expected number of URLs in urls_with_actions with a
    success result and that retrieving the first URL fails and the second succeeds.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.
        expected_url_results: The expected url results.

    Returns:
        Whether the test succeeded.
    """
    test_name = "delete"
    if not _check_url_count(
        urls_with_actions=urls_with_actions,
        expected_count=len(expected_url_results),
        test_name=test_name,
    ):
        return False

    if not _check_url_result(
        urls_with_actions=urls_with_actions,
        expected_result=expected_url_results,
        test_name=test_name,
    ):
        return False

    urls = tuple(urls_with_actions.keys())
    if not _check_url_retrieve(
        urls_with_actions={urls[1]: urls_with_actions[urls[1]]},
        discourse=discourse,
        test_name=test_name,
    ):
        return False

    with contextlib.suppress(DiscourseError):
        discourse.retrieve_topic(url=urls[0])
        logging.error(
            "%s check failed, topic not deleted, url: %s, urls_with_actions=%s",
            test_name,
            urls[0],
            urls_with_actions,
        )
        return False

    logging.info("%s check succeeded", test_name)
    return True


def cleanup(
    urls_with_actions: dict[str, str], discourse: Discourse, github_token: str, repo: str
) -> None:
    """Delete all URLs.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.
        github_token: Token for communication with GitHub.
        repo: The name of the repository.
    """
    for url in urls_with_actions.keys():
        with contextlib.suppress(DiscourseError):
            discourse.delete_topic(url=url)

    with contextlib.suppress(GithubException):
        github_client = Github(login_or_token=github_token)
        github_repo = github_client.get_repo(repo)
        update_branch = github_repo.get_git_ref(f"heads/{_UPDATE_BRANCH}")
        update_branch.delete()


if __name__ == "__main__":
    main()
