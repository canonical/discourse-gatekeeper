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

from src import GETTING_STARTED, exceptions, pre_flight_checks, run_migrate, run_reconcile, types_
from src.clients import get_clients
from src.constants import DEFAULT_BRANCH

GITHUB_HEAD_REF_ENV_NAME = "GITHUB_HEAD_REF"
GITHUB_OUTPUT_ENV_NAME = "GITHUB_OUTPUT"

T = typing.TypeVar("T")


def _parse_env_vars() -> types_.UserInputs:
    """Instantiate user inputs from environment variables.

    Raises:
        InputError: If required information is not provided as input.

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
    base_branch = os.getenv("INPUT_BASE_BRANCH", DEFAULT_BRANCH)

    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        raise exceptions.InputError(
            "Path to GitHub event information not found, is this action running on GitHub?"
        )
    event = json.loads(pathlib.Path(event_path).read_text(encoding="utf-8"))
    try:
        commit_sha = event["pull_request"]["head"]["sha"]
    except KeyError:
        # Use the commit SHA if not running as a pull request
        commit_sha = os.environ["GITHUB_SHA"]

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
        commit_sha=commit_sha,
        base_branch=base_branch,
    )


def _serialize_for_github(urls_with_actions_dict: dict[str, str]) -> str:
    """Serialize dictionary output into a string to be outputted to GitHub.

    Args:
        urls_with_actions_dict: dictionary output representing results of processes

    Returns:
        string representing the dictionary to be outputted to GitHub
    """
    compact_json = partial(json.dumps, separators=(",", ":"))

    return compact_json(urls_with_actions_dict)


def _write_github_output(
    **urls_with_actions_dicts: dict[str, str],
) -> None:
    """Writes results produced by the action to github_output.

    Args:
        urls_with_actions_dicts: list of key value pairs of link to result of action.

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

    output: str = "".join(
        f"{key}={_serialize_for_github(urls_with_actions_dict)}\n"
        for key, urls_with_actions_dict in urls_with_actions_dicts.items()
    )

    logging.info("Output: %s", output)

    pathlib.Path(github_output).write_text(output, encoding="utf-8")


def execute_in_tmpdir(func: typing.Callable[..., T]) -> typing.Callable[..., T]:
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
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> T:
        """Wrapper to be used to running an external function on a temporary directory.

        Args:
            args: positional arguments of the external function
            kwargs: variable named arguments of the external function

        Returns:
            output of the wrapped external function
        """
        initial_cwd = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as tempdir_name:
                tempdir = Path(tempdir_name)
                execute_cwd = tempdir / "cwd"
                shutil.copytree(src=initial_cwd, dst=execute_cwd)
                os.chdir(execute_cwd)
                output = func(execute_cwd, *args, **kwargs)
        finally:
            os.chdir(initial_cwd)

        return output

    return wrapper


@execute_in_tmpdir
def main_migrate(path: Path, user_inputs: types_.UserInputs) -> dict:
    """Main to migrate content from Discourse to Git repository.

    Args:
        path: path of the git repository
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        dictionary representing the output of the process
    """
    clients = get_clients(user_inputs, path)
    return run_migrate(clients=clients, user_inputs=user_inputs)


@execute_in_tmpdir
def main_reconcile(path: Path, user_inputs: types_.UserInputs) -> dict:
    """Main to reconcile content from Git repository to Discourse.

    Args:
        path: path of the git repository
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        dictionary representing the output of the process
    """
    clients = get_clients(user_inputs, path)
    return run_reconcile(clients=clients, user_inputs=user_inputs)


@execute_in_tmpdir
def main_checks(path: Path, user_inputs: types_.UserInputs) -> bool:
    """Checks to make sure that the repository is in a consistent state.

    Args:
        path: path of the git repository
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        dictionary representing the output of the process
    """
    clients = get_clients(user_inputs, path)
    return pre_flight_checks(clients=clients, user_inputs=user_inputs)


def main() -> None:
    """Execute the action."""
    logging.basicConfig(level=logging.INFO)

    # Read input
    user_inputs = _parse_env_vars()

    assert main_checks(user_inputs=user_inputs)  # pylint: disable=E1120

    # Push data to Discourse, avoiding community conflicts
    reconcile_urls_with_actions = main_reconcile(user_inputs=user_inputs)  # pylint: disable=E1120

    # Open a PR with community contributions if necessary
    migrate_urls_with_actions = main_migrate(user_inputs=user_inputs)  # pylint: disable=E1120

    # Write output
    _write_github_output(migrate=migrate_urls_with_actions, reconcile=reconcile_urls_with_actions)


if __name__ == "__main__":
    main()
