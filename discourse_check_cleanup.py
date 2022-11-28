#!/usr/bin/env python

# # Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Cleanup utility after running the action, primarily for testing purposes."""

import argparse
import contextlib
import json
import logging

from src.discourse import create_discourse, Discourse
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

    if not args.check_only:
        for url in urls_with_actions.keys():
            with contextlib.suppress(DiscourseError):
                discourse.delete_topic(url=url)

    exit(0 if check_result else 1)


def check_draft(urls_with_actions: dict[str, str]) -> bool:
    """Check that the draft test succeeded.

    Success is indicated by that there are no URLs with actions.

    Args:
        urls_with_actions: The URLs that had any actions against them.

    Returns:
        Whether the test succeeded.
    """
    if not urls_with_actions:
        logging.info("draft check succeeded")
        return True

    logging.error("create check failed, more than 0 URLs with actions: %s", urls_with_actions)
    return False


def check_create(urls_with_actions: dict[str, str], discourse: Discourse) -> bool:
    """Check that the create test succeeded.

    Success is indicated by that there are 2 URLs with a success result and that retrieving the
    URLs succeeds.

    Args:
        urls_with_actions: The URLs that had any actions against them.
        discourse: Client to the documentation server.

    Returns:
        Whether the test succeeded.
    """
    if len(urls_with_actions) != 2:
        logging.error("create check failed, fewer than 2 URLs with actions: %s", urls_with_actions)
        return False

    if not all(result == ActionResult.SUCCESS.value for result in urls_with_actions.values()):
        logging.error(
            "create check failed, not all URLs have success result: %s", urls_with_actions
        )
        return False

    for url in urls_with_actions.keys():
        try:
            discourse.retrieve_topic(url=url)
        except DiscourseError as exc:
            logging.error(
                "create check failed, URL retrieval failed for %s, %s", url, urls_with_actions
            )
            return False

    logging.info("create check succeeded")
    return True


if __name__ == "__main__":
    main()
