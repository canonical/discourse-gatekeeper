# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Execute the uploading of documentation."""

from pathlib import Path

import yaml

from .discourse import Discourse
from .exceptions import DiscourseError, InputError, ServerError
from .types_ import Page

METADATA_FILENAME = "metadata.yaml"
METADATA_DOCS_KEY = "docs"
METADATA_NAME_KEY = "name"
DOCUMENTATION_FOLDER_NAME = "docs"
DOCUMENTATION_INDEX_FILENAME = "index.md"


def _get_metadata(base_path: Path) -> dict:
    """Check for and read the metadata.

    Raises InputError if the metadata file does not exists or is malformed.

    Args:
        base_path: The base path to look for the metadata file in.

    Returns:
        The contents of the metadata file.

    """
    metadata_yaml = base_path / METADATA_FILENAME
    if not metadata_yaml.is_file():
        raise InputError(f"Could not find {METADATA_FILENAME} file, looked in folder: {base_path}")

    try:
        metadata = yaml.safe_load(metadata_yaml.read_text())
    except yaml.error.YAMLError as exc:
        raise InputError(
            f"Malformed {METADATA_FILENAME} file, read file: {metadata_yaml}"
        ) from exc

    if not metadata:
        raise InputError(f"{METADATA_FILENAME} file is empty, read file: {metadata_yaml}")
    if not isinstance(metadata, dict):
        raise InputError(
            f"{METADATA_FILENAME} file does not contain a mapping at the root, "
            f"read file: {metadata_yaml}, content: {metadata!r}"
        )

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
        raise InputError(f"{key!r} not defined in {METADATA_FILENAME}, {metadata=!r}")
    if not isinstance(docs_value := metadata[key], str):
        raise InputError(f"{key!r} is not a string in {METADATA_FILENAME}, {metadata=!r}")
    if not docs_value:
        raise InputError(f"{key!r} is empty in {METADATA_FILENAME}, {metadata=!r}")
    return docs_value


def _read_docs_index(base_path: Path) -> str:
    """Read the content of the index file.

    Raises InputError if the file does not exist.

    Args:
        base_path: The starting path to look for the index content.

    Returns:
        The content of the index file.

    """
    if not (docs_folder := base_path / DOCUMENTATION_FOLDER_NAME).is_dir():
        raise InputError(
            f"Could not find directory '{docs_folder}' which is where documentation is expected "
            "to be stored"
        )
    if not (index_file := docs_folder / DOCUMENTATION_INDEX_FILENAME).is_file():
        raise InputError(
            f"Could not find file '{index_file}' which is where the documentation index file is "
            "expected to be stored"
        )

    return index_file.read_text()


def retrieve_or_create_index(
    create_if_not_exists: bool, base_path: Path, server_client: Discourse
) -> Page:
    """Retrieve the index page defined in the metadata file or create it if it doesn't exist.

    This function is designed to ensure that the index documentation page exists for a charm and to
    return its content and url. There are two cases, if the docs key is in the metadata file, it
    indicates that the charm already has documentation published. In that case, the url is the
    value of the docs key and the content is retrieved from the server. If the docs key is not in
    the metadata file, it indicates that the charm does not currently have documentation published.
    In that case, the index documentation is published based on the contents of the index file in
    the docs folder and the url is set based on the response from the server.

    Raises InputError if create_if_not_exists is False and the docs key is not defined in the
    metadata file. Raises ServerError if interactions with the documentation server (retrieving or
    creating the index page) occurs.

    Args:
        create_if_not_exists: Whether to create the index page if it does not exist.
        base_path: The base path to look for the metadata file in.
        server_client: A client to the documentation server.

    Returns:
        The index page.

    """
    metadata = _get_metadata(base_path=base_path)

    if METADATA_DOCS_KEY not in metadata and not create_if_not_exists:
        raise InputError(
            f"'{METADATA_DOCS_KEY!r}' not defined in {METADATA_FILENAME} and "
            f"'create_if_not_exists' false, {metadata=!r}"
        )

    # The charm does not have any documentation on the server, creating the index page using the
    # content in the local index file
    if METADATA_DOCS_KEY not in metadata and create_if_not_exists:
        name_value = _get_key(metadata=metadata, key=METADATA_NAME_KEY)
        content = _read_docs_index(base_path=base_path)

        try:
            index_url = server_client.create_topic(
                title=f"{name_value.replace('-', ' ').title()} Documentation Overview",
                content=content,
            )
        except DiscourseError as exc:
            raise ServerError("Index page creation failed") from exc
    # The charm already has documentation on the server, retrieving the content based on the docs
    # key in the metadata
    else:
        index_url = _get_key(metadata=metadata, key=METADATA_DOCS_KEY)
        try:
            content = server_client.retrieve_topic(url=index_url)
        except DiscourseError as exc:
            raise ServerError("Index page retrieval failed") from exc

    return Page(url=index_url, content=content)
