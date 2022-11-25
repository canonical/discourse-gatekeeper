# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper functions for tests."""

from pathlib import Path

from src import index


def create_metadata_yaml(content: str, path: Path) -> None:
    """Create the metadata file.

    Args:
        content: The text to be written to the file.
        path: The directory to create the file in.

    """
    metadata_yaml = path / index.METADATA_FILENAME
    metadata_yaml.write_text(content, encoding="utf-8")
