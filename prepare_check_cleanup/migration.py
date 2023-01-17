# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility for running the migration action, primarily for testing purposes."""

import argparse
import json
import logging
import os
import sys
from enum import Enum
from pathlib import Path

from github import Github

from src.discourse import Discourse, create_discourse
from src.pull_request import create_repository_client
from src.reconcile import NAVIGATION_TABLE_START


class Action(str, Enum):
    """The actions the utility can take.

    Attrs:
        PREPARE: Prepare discourse pages before running the migration.
        CLEANUP: Delete discourse pages before after the migration.
    """

    PREPARE = "prepare"
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
        "discourse_config", help="The discourse configuration used to create the pages"
    )
    parser.add_argument(
        "--action", help="Action to run", choices=tuple(action.value for action in Action)
    )
    parser.add_argument(
        "--action-kwargs", help="Arguments for the action as a JSON mapping", default="{}"
    )
    args = parser.parse_args()
    discourse_config = json.loads(args.discourse_config)
    action_kwargs = json.loads(args.action_kwargs)

    discourse = create_discourse(**discourse_config)

    match args.action:
        case Action.PREPARE.value:
            prepare(discourse=discourse, **action_kwargs)
            sys.exit(0)
        case Action.CLEANUP.value:
            cleanup(discourse=discourse, **action_kwargs)
            sys.exit(0)
        case _:
            raise NotImplementedError(f"{args.action} has not been implemented")


def prepare(index_filename: str, page_filename: str, discourse: Discourse) -> None:
    """Create the content and index page.

    Args:
        index_filename: The path to the file with the index file contents. The first line will be
            used as the title and the content will be used as the topic content.
        page_filename: The path to the file with the content file contents. The first line will
            be used as the title and the content will be used as the topic content.
        discourse: Client to the documentation server.
    """
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


def cleanup(
    topics: dict[str, str],
    github_access_token: str,
    discourse: Discourse,
) -> None:
    """Create the content and index page.

    Args:
        topics: The discourse topics created for the migration.
        github_access_token: The secret required for interactions with GitHub.
        discourse: Client to the documentation server.
    """
    for topic_url in topics.values():
        discourse.delete_topic(url=topic_url)

    repository = create_repository_client(access_token=github_access_token, base_path=Path())
    repository.cleanup_migration()


if __name__ == "__main__":
    main()
