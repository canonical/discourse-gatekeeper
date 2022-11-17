#!/usr/bin/env python

# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main execution for the action."""

import json
import os
import pathlib
from functools import partial

from src.discourse import create_discourse
from src.run import retrieve_or_create_index


def main():
    """Execute the action."""
    # Read input
    create_new_topic = os.getenv("INPUT_CREATE_NEW_TOPIC") == "true"
    discourse_host = os.getenv("INPUT_DISCOURSE_HOST")
    discourse_category_id = os.getenv("INPUT_DISCOURSE_CATEGORY_ID")
    discourse_api_username = os.getenv("INPUT_DISCOURSE_API_USERNAME")
    discourse_api_key = os.getenv("INPUT_DISCOURSE_API_KEY")

    # Execute action
    create_discourse_kwargs = {
        "hostname": discourse_host,
        "category_id": discourse_category_id,
        "api_username": discourse_api_username,
        "api_key": discourse_api_key,
    }
    discourse = create_discourse(**create_discourse_kwargs)
    page = retrieve_or_create_index(
        create_if_not_exists=create_new_topic, base_path=pathlib.Path(), server_client=discourse
    )

    # Write output
    github_output = pathlib.Path(os.getenv("GITHUB_OUTPUT"))
    compact_json = partial(json.dumps, separators=(",", ":"))
    created_pages = compact_json({"index": page.url})
    discourse_config = compact_json(create_discourse_kwargs)
    with github_output.open("w", encoding="utf-8") as github_output_file:
        github_output_file.write(f"created_pages={created_pages}\n")
        github_output_file.write(f"discourse_config={discourse_config}\n")


if __name__ == "__main__":
    main()
