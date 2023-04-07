#!/usr/bin/env python

# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main execution for the action."""

import functools
import json
import logging
import os
import pathlib
import shutil
import tempfile
import typing
from functools import partial
from pathlib import Path

from src import GETTING_STARTED, exceptions, types_, Clients, run_migrate, run_reconcile
from src.discourse import create_discourse
from src.repository import create_repository_client

GITHUB_HEAD_REF_ENV_NAME = "GITHUB_HEAD_REF"
GITHUB_OUTPUT_ENV_NAME = "GITHUB_OUTPUT"

T = typing.TypeVar("T")


def _parse_env_vars() -> types_.UserInputs:
    """Instantiate user inputs from environment variables.

    Returns:
        Wrapped user input variables.
    """
    discourse_host = os.getenv("INPUT_DISCOURSE_HOST", "")
    discourse_category_id = os.getenv("INPUT_DISCOURSE_CATEGORY_ID", "")
    discourse_api_username = os.getenv("INPUT_DISCOURSE_API_USERNAME", "")
    discourse_api_key = os.getenv("INPUT_DISCOURSE_API_KEY", "")
    delete_topics = os.getenv("INPUT_DELETE_TOPICS") == "true"
    dry_run = os.getenv("INPUT_DRY_RUN") == "true"
    github_access_token = os.getenv("INPUT_GITHUB_TOKEN")
    base_branch = os.getenv("INPUT_BASE_BRANCH")

    return types_.UserInputs(
        discourse=types_.UserInputsDiscourse(
            hostname=discourse_host,
            category_id=discourse_category_id,
            api_username=discourse_api_username,
            api_key=discourse_api_key,
        ),
        delete_pages=delete_topics,
        dry_run=dry_run,
        github_access_token=github_access_token,
        base_branch=base_branch,
    )


def _write_github_output(urls_with_actions_dict: dict[str, str]) -> None:
    """Writes results produced by the action to github_output.

    Args:
        urls_with_actions_dict: key value pairs of link to result of action.

    Raises:
        InputError: if not running inside a github actions environment.
    """
    github_output = os.getenv(GITHUB_OUTPUT_ENV_NAME)
    if not github_output:
        raise exceptions.InputError(
            f"Invalid '{GITHUB_OUTPUT_ENV_NAME}' input, it must be non-empty, got"
            f"{github_output=!r}. This action is intended to run inside github-actions. "
            f"{GETTING_STARTED}"
        )

    github_output_path = pathlib.Path(github_output)
    compact_json = partial(json.dumps, separators=(",", ":"))
    urls_with_actions = compact_json(urls_with_actions_dict)
    if urls_with_actions_dict:
        *_, index_url = urls_with_actions_dict.keys()
    else:
        index_url = ""
    github_output_path.write_text(
        f"urls_with_actions={urls_with_actions}\nindex_url={index_url}\n",
        encoding="utf-8",
    )


def execute_in_tmpdir(func: typing.Callable[[pathlib.Path], T]) -> typing.Callable[[], T]:
    """Execute a function in a temporary directory.

    Makes a copy of the current working directory in a temporary directory, changes the working
    directory to that directory, executes the function, changes the working directory back and
    deletes the temporary directory.

    Args:
        func: The function to run in a temporary directory.

    Returns:
        The wrapper for the function that executes it in a temporary directory.
    """

    @functools.wraps(func)
    def wrapper() -> T:
        """Replacement function."""
        initial_cwd = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as tempdir_name:
                tempdir = Path(tempdir_name)
                execute_cwd = tempdir / "cwd"
                shutil.copytree(src=initial_cwd, dst=execute_cwd)
                os.chdir(execute_cwd)
                output = func(execute_cwd)
        finally:
            os.chdir(initial_cwd)

        return output

    return wrapper


def get_clients(user_inputs: types_.UserInputs, base_path: pathlib.Path) -> Clients:
    return Clients(
        discourse=create_discourse(
            hostname=user_inputs.discourse.hostname,
            category_id=user_inputs.discourse.category_id,
            api_username=user_inputs.discourse.api_username,
            api_key=user_inputs.discourse.api_key,
        ),
        repository=create_repository_client(
            access_token=user_inputs.github_access_token,
            base_path=base_path
        )
    )


@execute_in_tmpdir
def main() -> None:
    """Execute the action."""
    logging.basicConfig(level=logging.INFO)

    # Read input
    user_inputs = _parse_env_vars()

    # Run this only if the reference to discourse exists
    clients = get_clients(user_inputs, pathlib.Path())

    # Open a PR with community contributions if necessary
    migrate_result = execute_in_tmpdir(
        lambda tmp_path: run_migrate(
            clients=get_clients(user_inputs, tmp_path), user_inputs=user_inputs)
    )() if clients.repository.metadata.docs else {}

    # Push data to Discourse, avoiding community conflicts
    reconcile_result = execute_in_tmpdir(
        lambda tmp_path: run_reconcile(
            clients=get_clients(user_inputs, tmp_path), user_inputs=user_inputs
        )
    )() if clients.repository.has_docs_directory else {}

    # Write output
    _write_github_output(
        urls_with_actions_dict=migrate_result | reconcile_result
    )


if __name__ == "__main__":
    main()
