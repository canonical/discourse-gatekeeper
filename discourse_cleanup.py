#!/usr/bin/env python

# # Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Cleanup utility after running the action, primarily for testing purposes."""

import argparse
import contextlib
import json

from src.discourse import create_discourse
from src.exceptions import DiscourseError


def main():
    """Clean up created Discourse pages."""
    parser = argparse.ArgumentParser(
        prog="DiscourseCleanup",
        description="Delete posts created on discourse during an action execution.",
    )
    parser.add_argument("urls_with_actions", help="The pages that were created during execution")
    parser.add_argument(
        "discourse_config", help="The discourse configuration used to create the pages"
    )
    args = parser.parse_args()
    urls_with_actions = json.loads(args.urls_with_actions)
    discourse_config = json.loads(args.discourse_config)

    discourse = create_discourse(**discourse_config)
    for url in urls_with_actions.keys():
        with contextlib.suppress(DiscourseError):
            discourse.delete_topic(url=url)


if __name__ == "__main__":
    main()
