# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Interactions with the documentation server."""

from pathlib import Path

import yaml

from .discourse import Discourse
from .exceptions import InputError, DiscourseError, ServerError
from .types_ import Page


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
    metadata_yaml_path = local_base_path / "metadata.yaml"
    if not metadata_yaml_path.is_file():
        raise InputError("Could not fine metadata.yaml file")

    with metadata_yaml_path.open(encoding="utf-8") as metadata_yaml_file:
        try:
            metadata = yaml.safe_load(metadata_yaml_file)
        except yaml.error.YAMLError as exc:
            raise InputError("Malformed metadata.yaml file") from exc

    # Check docs key
    docs_key = "docs"
    docs_not_defined = (
        not metadata
        or docs_key not in metadata
        or not metadata[docs_key]
        or not isinstance(metadata[docs_key], str)
    )
    if docs_not_defined and not create_if_not_exists:
        raise InputError(
            f"The {docs_key} key is not defined, empty or not a string in the metadata.yaml file "
            f"and creation of the index page has been disabled, {metadata=!r}"
        )

    if docs_not_defined:
        # Check name key
        name_key = "name"
        if (
            not metadata
            or name_key not in metadata
            or not metadata[name_key]
            or not isinstance(metadata[name_key], str)
        ):
            raise InputError(
                f"The {name_key} key is not defined, empty or not a string in the metadata.yaml file, "
                f"{metadata=!r}"
            )

        try:
            content = "placeholder content until it is created"
            url = server_client.create_topic(
                title=f"{metadata['name'].replace('-', ' ').title()} Documentation Overview",
                content=content,
            )
        except DiscourseError as exc:
            raise ServerError("Index page creation failed") from exc
    else:
        url = metadata[docs_key]
        try:
            content = server_client.retrieve_topic(url=url)
        except DiscourseError as exc:
            raise ServerError("Index page retrieval failed") from exc

    return Page(url=url, content=content)
