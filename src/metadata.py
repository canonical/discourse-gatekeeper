# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for parsing metadata.yaml file."""

from pathlib import Path

import yaml

from . import types_
from .exceptions import InputError

METADATA_DOCS_KEY = "docs"
METADATA_FILENAME = "metadata.yaml"
METADATA_NAME_KEY = "name"


def get(path: Path) -> types_.Metadata:
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

    if METADATA_NAME_KEY not in metadata:
        raise InputError(
            f"Could not find required key: {METADATA_NAME_KEY}, "
            f"read file: {metadata_yaml}, content: {metadata!r}"
        )
    if not isinstance(name := metadata[METADATA_NAME_KEY], str):
        raise InputError(f"Invalid value for name key: {name}, expected a string value")

    docs = metadata.get(METADATA_DOCS_KEY)
    if not isinstance(docs, str | None) or (METADATA_DOCS_KEY in metadata and docs is None):
        raise InputError(f"Invalid value for docs key: {docs}, expected a string value")

    return types_.Metadata(name=name, docs=docs)
