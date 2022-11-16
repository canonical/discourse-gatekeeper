#!/usr/bin/env python
#
# # Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Cleanup utility after running the action, primarily for testing purposes."""

import argparse
import json

from src.discourse import create_discourse


def main():
    """Clean up created Discourse pages."""
    parser = argparse.ArgumentParser(
        prog="DiscourseCleanup",
        description="Delete posts created on discourse during an action execution.",
    )
    parser.add_argument(
        "created_pages",
        help="The pages that were created during execution",
        required=True,
    )
    parser.add_argument(
        "discourse_config",
        help="The discourse configuration used to create the pages",
        required=True,
    )
    args = parser.parse_args()
    created_pages = json.loads(args.created_pages)
    discourse_config = json.loads(args.discourse_config)

    discourse = create_discourse(**discourse_config)
    for url in created_pages:
        discourse.delete_topic(url=url)


if __name__ == "__main__":
    main()
