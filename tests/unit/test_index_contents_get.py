# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for index module get_contents function."""

import typing
from pathlib import Path

import pytest

from src import index, types_

from .. import factories


def _test_get_contents_parameters():
    """Generate parameters for the test_get_contents test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), (), (), id="empty"),
        pytest.param(
            (title_1 := "title 1",),
            (value_1 := "file_1.md",),
            ("file",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single file",
        ),
        pytest.param(
            (title_1 := "title 1",),
            (value_1 := "dir_1",),
            ("dir",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single directory",
        ),
        pytest.param(
            (title_1 := "title 1", title_2 := "title 2"),
            (value_1 := "file_1.md", value_2 := "file_2.md"),
            ("file", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=1
                ),
            ),
            id="multiple files",
        ),
        pytest.param(
            (title_1 := "title 1", title_2 := "title 2"),
            (value_1 := "dir_1", value_2 := "dir_2"),
            ("dir", "dir"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=1
                ),
            ),
            id="multiple directories",
        ),
        pytest.param(
            (title_1 := "title 1", title_2 := "title 2"),
            (value_1 := "file_1.md", value_2 := "dir_2"),
            ("file", "dir"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=1
                ),
            ),
            id="file and directory",
        ),
    ]


@pytest.mark.parametrize(
    "reference_titles, reference_paths, create_paths, expected_items",
    _test_get_contents_parameters(),
)
def test_get_contents(
    reference_titles: tuple[str, ...],
    reference_paths: tuple[str, ...],
    create_paths: tuple[typing.Literal["file", "dir"], ...],
    expected_items: tuple[types_.IndexContentsListItem, ...],
    tmp_path: Path,
):
    """
    arrange: given the index file contents
    act: when get_contents_list_items is called with the index file
    assert: then the expected contents list items are returned.
    """
    # Create the paths
    for reference_path, create_path in zip(reference_paths, create_paths):
        match create_path:
            case "file":
                (tmp_path / reference_path).touch()
            case "dir":
                (tmp_path / reference_path).mkdir(parents=True)

    content_items = "\n".join(
        f"- [{reference_title}]({reference_path})"
        for reference_title, reference_path in zip(reference_titles, reference_paths)
    )
    index_file = types_.IndexFile(title="title 1", content=f"# Contents\n{content_items}\n")

    returned_items = tuple(index.get_contents(index_file=index_file, docs_path=tmp_path))

    assert returned_items == expected_items
