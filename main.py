# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main execution for the action."""

import os
import pathlib

from src.discourse import create_discourse
from src.server import retrieve_or_create_index


def main():
    """Execute the action."""
    # Read input
    create_new_topic = os.environ["INPUT_CREATE_NEW_TOPIC"] == "true"
    discourse_host = os.environ["INPUT_DISCOURSE_HOST"]
    discourse_category_id = int(os.environ["INPUT_DISCOURSE_CATEGORY_ID"])
    print(create_new_topic)
    print(discourse_host)
    print(discourse_category_id)

    # Execute action
    discourse = create_discourse(hostname=discourse_host, category_id=discourse_category_id)
    page = retrieve_or_create_index(
        create_if_not_exists=create_new_topic,
        local_base_path=pathlib.Path(),
        server_client=discourse,
    )
    print(page)


if __name__ == "__main__":
    main()
