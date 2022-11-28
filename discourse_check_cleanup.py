#!/usr/bin/env python

# # Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Cleanup utility after running the action, primarily for testing purposes."""

import argparse
import contextlib
import json
import logging
import typing

from src.discourse import Discourse, create_discourse
from src.exceptions import DiscourseError
from src.types_ import ActionResult


def main():
    """Clean up created Discourse pages."""
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        prog="DiscourseCleanup",
        description="Delete posts created on discourse during an action execution.",
    )
    parser.add_argument("urls_with_actions", help="The pages that were created during execution")
    parser.add_argument(
        "discourse_config", help="The discourse configuration used to create the pages"
    )
    parser.add_argument(
        "--check-draft", help="Check that the draft test succeeded", action="store_true"
    )
    parser.add_argument(
        "--check-create", help="Check that the create test succeeded", action="store_true"
    )
    parser.add_argument(
        "--check-delete-topics",
        help="Check that the delete_topics test succeeded",
        action="store_true",
    )
    parser.add_argument(
        "--check-delete", help="Check that the delete test succeeded", action="store_true"
    )
    parser.add_argument(
        "--check-only", help="Skip cleanup and only run any checks", action="store_true"
    )
    args = parser.parse_args()
    urls_with_actions = json.loads(args.urls_with_actions)
    discourse_config = json.loads(args.discourse_config)

    discourse = create_discourse(**discourse_config)

    check_result = True
    if args.check_draft:
        check_result = check_draft(urls_with_actions=urls_with_actions)
    if args.check_create:
        check_result = check_create(urls_with_actions=urls_with_actions, discourse=discourse)
    if args.check_delete_topics:
        check_result = check_delete_topics(
            urls_with_actions=urls_with_actions, discourse=discourse
        )

    if not args.check_only:
        for url in urls_with_actions.keys():
            with contextlib.suppress(DiscourseError):
                discourse.delete_topic(url=url)

    exit(0 if check_result else 1)


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
            "expected: %s, got: %s, urls_with_actions=%s",
            test_name,
            results,
            expected_result,
            urls_with_actions,
        )
        return False
    return True


def check_draft(urls_with_actions: dict[str, str]) -> bool:
    """Check that the draft test succeeded.

    Success is indicated by that there are no URLs with actions.

    Args:
        urls_with_actions: The URLs that had any actions against them.

    Returns:
        Whether the test succeeded.
    """
    test_name = "draft"
    if not _check_url_count(
        urls_with_actions=urls_with_actions, expected_count=0, test_name=test_name
    ):
        return False

    logging.info("%s check succeeded", test_name)
    return True


def check_create(urls_with_actions: dict[str, str], discourse: Discourse) -> bool:
    """Check that the create test succeeded.

    Success is indicated by that there are 3 URLs with a success result and that retrieving the
    URLs succeeds.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.

    Returns:
        Whether the test succeeded.
    """
    test_name = "create"
    if not _check_url_count(
        urls_with_actions=urls_with_actions, expected_count=3, test_name=test_name
    ):
        return False

    if not _check_url_result(
        urls_with_actions=urls_with_actions,
        expected_result=[
            ActionResult.SUCCESS.value,
            ActionResult.SUCCESS.value,
            ActionResult.SUCCESS.value,
        ],
    ):
        return False

    if not _check_url_retrieve(
        urls_with_actions=urls_with_actions, discourse=discourse, test_name=test_name
    ):
        return False

    logging.info("%s check succeeded", test_name)
    return True


def check_delete_topics(urls_with_actions: dict[str, str], discourse: Discourse) -> bool:
    """Check that the delete_topics test succeeded.

    Success is indicated by that there are 3 URLs with 2 success and 1 skip result and that
    retrieving the URLs succeeds (none have been deleted).

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.

    Returns:
        Whether the test succeeded.
    """
    test_name = "delete_topics"
    if not _check_url_count(
        urls_with_actions=urls_with_actions, expected_count=3, test_name=test_name
    ):
        return False

    if not _check_url_result(
        urls_with_actions=urls_with_actions,
        expected_result=[
            ActionResult.SUCCESS.value,
            ActionResult.SKIP.value,
            ActionResult.SUCCESS.value,
        ],
    ):
        return False

    if not _check_url_retrieve(
        urls_with_actions=urls_with_actions, discourse=discourse, test_name=test_name
    ):
        return False

    logging.info("%s check succeeded", test_name)
    return True


if __name__ == "__main__":
    main()
