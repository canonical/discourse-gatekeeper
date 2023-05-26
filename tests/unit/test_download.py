# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for download."""

import pytest

from src import DOCUMENTATION_FOLDER_NAME, DOCUMENTATION_TAG, constants  # GETTING_STARTED,
from src.download import recreate_docs
from src.metadata import METADATA_DOCS_KEY, METADATA_NAME_KEY

from .helpers import create_metadata_yaml

# Need access to protected functions for testing
# pylint: disable=protected-access


@pytest.mark.usefixtures("patch_create_repository_client")
def test_recreate_docs(
    mocked_clients,
):
    """
    arrange: given a path with a metadata.yaml that has docs key and no docs directory
        and mocked discourse
    act: when recreate_docs is called
    assert: then docs from the server is migrated into local docs path, creating the tree-structure
    """
    repository_path = mocked_clients.repository.base_path

    create_metadata_yaml(
        content=f"{METADATA_NAME_KEY}: name 1\n" f"{METADATA_DOCS_KEY}: docsUrl",
        path=repository_path,
    )
    index_content = """Content header to be download.

    Content body.\n"""
    index_table = f"""{constants.NAVIGATION_TABLE_START}
    | 1 | page-path-1 | [empty-navlink]() |
    | 2 | page-file-1 | [file-navlink](/file-navlink) |"""
    index_page = f"{index_content}{index_table}"
    navlink_page = "file-navlink-content"
    mocked_clients.discourse.retrieve_topic.side_effect = [index_page, navlink_page]

    recreate_docs(mocked_clients, DOCUMENTATION_TAG)

    assert (index_file := repository_path / DOCUMENTATION_FOLDER_NAME / "index.md").is_file()
    assert (
        path_file := repository_path / DOCUMENTATION_FOLDER_NAME / "page-path-1" / "page-file-1.md"
    ).is_file()
    assert index_file.read_text(encoding="utf-8") == index_content
    assert path_file.read_text(encoding="utf-8") == navlink_page
