# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Interactions with the documentation server."""

from pathlib import Path
import typing

import yaml

from .discourse import Discourse
from .exceptions import InputError, DiscourseError, ServerError
from .types_ import Page


def _get_metadata(local_base_path: Path) -> dict:
    """Check for and read the metadata.

    Raises InputError if the metadata.yaml file does not exists or is malformed.

    Args:
        local_base_path: The base path to look for the metadata.yaml file in.

    Returns:
        The contents of the metadata.yaml file.

    """
    metadata_yaml_path = local_base_path / "metadata.yaml"
    if not metadata_yaml_path.is_file():
        raise InputError("Could not find metadata.yaml file")

    with metadata_yaml_path.open(encoding="utf-8") as metadata_yaml_file:
        try:
            metadata = yaml.safe_load(metadata_yaml_file)
        except yaml.error.YAMLError as exc:
            raise InputError("Malformed metadata.yaml file") from exc

    if not metadata:
        raise InputError("metadata.yaml file is empty")
    if not isinstance(metadata, dict):
        raise InputError("metadata.yaml file does not contain a mapping at the root")

    return metadata


def _get_key(metadata: dict, key: str) -> str:
    """Check and return the key value from the metadata.

    Raises InputError if key does not exists, is empty or not a string.

    Args:
        metadata: The metadata to retrieve the key from.

    Returns:
        The value of the key.

    """
    if key not in metadata:
        raise InputError(f"{key!r} not defined in metadata.yaml, {metadata=!r}")
    if not isinstance(docs_value := metadata[key], str):
        raise InputError(f"{key!r} is not a string in metadata.yaml, {metadata=!r}")
    if not docs_value:
        raise InputError(f"{key!r} is empty in metadata.yaml, {metadata=!r}")
    return docs_value


def retrieve_or_create_index(
    create_if_not_exists: bool, local_base_path: Path, server_client: Discourse
) -> Page:
    """Retrieve the index page defined in the metadata.yaml file or create it if it doesn't exist.

    Raises InputError if the metadata.yaml file does not exists or is malformed or if docs key does
    not exists, is empty or not a string and create_if_not_exists is False. Raises InputError if
    create_if_not_exists is True and the name key does not exists or is empty or not a string in
    metadata.yaml. Raises ServerError if interactions with the documentation server (retrieving or
    creating the index page) occurs.

    Args:
        create_if_not_exists: Whether to create the index page if it does not exist.
        local_base_path: The base path to look for the metadata.yaml file in.
        server_client: A client to the documentation server.

    Returns:
        The index page.

    """
    metadata = _get_metadata(local_base_path=local_base_path)

    # Check docs key
    docs_key = "docs"
    if docs_key not in metadata and create_if_not_exists:
        # Check name key
        name_key = "name"
        name_value = _get_key(metadata=metadata, key=name_key)

        try:
            content = "placeholder content until it is created"
            index_url = server_client.create_topic(
                title=f"{name_value.replace('-', ' ').title()} Documentation Overview",
                content=content,
            )
        except DiscourseError as exc:
            raise ServerError("Index page creation failed") from exc
    elif docs_key not in metadata and not create_if_not_exists:
        raise InputError(
            f"'{docs_key!r}' not defined in metadata.yaml and 'create_if_not_exists' false, "
            f"{metadata=!r}"
        )
    else:
        index_url = _get_key(metadata=metadata, key=docs_key)
        try:
            content = server_client.retrieve_topic(url=index_url)
        except DiscourseError as exc:
            raise ServerError("Index page retrieval failed") from exc

    return Page(url=index_url, content=content)
