# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Execute the uploading of documentation."""

from pathlib import Path

import yaml

from .discourse import Discourse
from .exceptions import DiscourseError, InputError, ServerError
from .types_ import Index, IndexFile, Page

METADATA_FILENAME = "metadata.yaml"
METADATA_DOCS_KEY = "docs"
METADATA_NAME_KEY = "name"
DOCUMENTATION_FOLDER_NAME = "docs"
DOCUMENTATION_INDEX_FILENAME = "index.md"


def _get_metadata(path: Path) -> dict:
    """Check for and read the metadata.

    Args:
        path: The base path to look for the metadata file in.

    Returns:
        The contents of the metadata file.

    Raises:
        InputError: if the metadata file does not exists or is malformed.

    """
    metadata_yaml = path / METADATA_FILENAME
    if not metadata_yaml.is_file():
        raise InputError(f"Could not find {METADATA_FILENAME} file, looked in folder: {path}")

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

    Args:
        metadata: The metadata to retrieve the key from.

    Returns:
        The value of the key.

    Raises:
        InputError: if key does not exists, is empty or not a string.

    """
    if key not in metadata:
        raise InputError(f"{key!r} not defined in {METADATA_FILENAME}, {metadata=!r}")
    if not isinstance(docs_value := metadata[key], str):
        raise InputError(f"{key!r} is not a string in {METADATA_FILENAME}, {metadata=!r}")
    if not docs_value:
        raise InputError(f"{key!r} is empty in {METADATA_FILENAME}, {metadata=!r}")
    return docs_value


def _read_docs_index(base_path: Path) -> str | None:
    """Read the content of the index file.

    Args:
        base_path: The starting path to look for the index content.

    Returns:
        The content of the index file if it exists, otherwise return None.

    """
    if not (docs_directory := base_path / DOCUMENTATION_FOLDER_NAME).is_dir():
        return None
    if not (index_file := docs_directory / DOCUMENTATION_INDEX_FILENAME).is_file():
        return None

    return index_file.read_text()


def get(base_path: Path, server_client: Discourse) -> Index:
    """Retrieve the local and server index information.

    Args:
        base_path: The base path to look for the metadata file in.
        server_client: A client to the documentation server.

    Returns:
        The index page.

    Raises:
        ServerError: if interactions with the documentation server occurs.

    """
    metadata = _get_metadata(path=base_path)

    if METADATA_DOCS_KEY in metadata:
        index_url = _get_key(metadata=metadata, key=METADATA_DOCS_KEY)
        try:
            server_content = server_client.retrieve_topic(url=index_url)
        except DiscourseError as exc:
            raise ServerError("Index page retrieval failed") from exc
        server = Page(url=index_url, content=server_content)
    else:
        server = None

    name_value = _get_key(metadata=metadata, key=METADATA_NAME_KEY)
    local_content = _read_docs_index(base_path=base_path)
    local = IndexFile(
        title=f"{name_value.replace('-', ' ').title()} Documentation Overview",
        content=local_content,
    )

    return Index(server=server, local=local)
