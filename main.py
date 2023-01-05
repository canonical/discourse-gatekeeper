#!/usr/bin/env python

# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main execution for the action."""

import json
import logging
import os
import pathlib
from functools import partial

from src import run, types_
from src.discourse import create_discourse


# pylint: disable=too-many-locals
def main() -> None:
    """Execute the action."""
    logging.basicConfig(level=logging.INFO)

    # Read input
    delete_topics = os.getenv("INPUT_DELETE_TOPICS") == "true"
    dry_run = os.getenv("INPUT_DRY_RUN") == "true"
    discourse_host = os.getenv("INPUT_DISCOURSE_HOST")
    discourse_category_id = os.getenv("INPUT_DISCOURSE_CATEGORY_ID")
    discourse_api_username = os.getenv("INPUT_DISCOURSE_API_USERNAME")
    discourse_api_key = os.getenv("INPUT_DISCOURSE_API_KEY")
    github_access_token = os.getenv("INPUT_GITHUB_TOKEN")

    # Execute action
    create_discourse_kwargs = {
        "hostname": discourse_host,
        "category_id": discourse_category_id,
        "api_username": discourse_api_username,
        "api_key": discourse_api_key,
    }
    base_path = pathlib.Path()
    discourse = create_discourse(**create_discourse_kwargs)
    urls_with_actions_dict = run(
        base_path=base_path,
        discourse=discourse,
        user_inputs=types_.UserInputs(
            dry_run=dry_run, delete_pages=delete_topics, github_access_token=github_access_token
        ),
    )

    # Write output
    github_output = pathlib.Path(os.getenv("GITHUB_OUTPUT", ""))
    compact_json = partial(json.dumps, separators=(",", ":"))
    urls_with_actions = compact_json(urls_with_actions_dict)
    if urls_with_actions_dict:
        *_, index_url = urls_with_actions_dict.keys()
    else:
        index_url = ""
    discourse_config = compact_json(create_discourse_kwargs)
    github_output.write_text(
        f"urls_with_actions={urls_with_actions}\n"
        f"index_url={index_url}\n"
        f"discourse_config={discourse_config}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
