#!/usr/bin/env python

# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main execution for the action."""

import json
import os
import pathlib
from functools import partial

from src.discourse import create_discourse
from src.server import retrieve_or_create_index


def main():
    """Execute the action."""
    # Read input
    create_new_topic = os.getenv("INPUT_CREATE_NEW_TOPIC") == "true"
    discourse_host = os.getenv("INPUT_DISCOURSE_HOST")
    discourse_category_id = int(os.getenv("INPUT_DISCOURSE_CATEGORY_ID"))

    # Execute action
    discourse = create_discourse(hostname=discourse_host, category_id=discourse_category_id)
    page = retrieve_or_create_index(
        create_if_not_exists=create_new_topic,
        local_base_path=pathlib.Path(),
        server_client=discourse,
    )

    # Write output
    github_output = pathlib.Path(os.getenv("GITHUB_OUTPUT"))
    compact_json = partial(json.dumps, separators=(",", ":"))
    with github_output.open("w", encoding="utf-8") as github_output_file:
        github_output_file.write(f"created_pages={compact_json({'index': page.url})}\n")
        github_output_file.write(
            f"discourse_config={compact_json({'hostname': discourse_host, 'category_id': discourse_category_id})}\n"
        )


if __name__ == "__main__":
    main()
