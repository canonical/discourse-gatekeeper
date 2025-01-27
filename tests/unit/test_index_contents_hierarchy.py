# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for index module _calculate_contents_hierarchy function."""

# Need access to protected functions for testing
# pylint: disable=protected-access

import typing
from pathlib import Path

import pytest

from gatekeeper import constants, exceptions, index, types_

from .. import factories
from .helpers import assert_substrings_in_string


def _test__calculate_contents_hierarchy_invalid_parameters():
    """Generate parameters for the test__calculate_contents_hierarchy_invalid test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="ftp://localhost",
                    rank=1,
                ),
            ),
            (),
            ("not", "file", "directory", "HTTP", repr(item)),
            id="invalid external reference",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="file_1.md",
                    rank=1,
                ),
            ),
            (),
            ("not", "file", "directory", "HTTP", repr(item)),
            id="file doesn't exist",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="file_1.txt",
                    rank=1,
                ),
            ),
            ("file",),
            ("not", "expected", "file type", constants.DOC_FILE_EXTENSION, repr(item)),
            id="file wrong extension",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 1",
                    reference_value="file_1.md",
                    rank=1,
                ),
            ),
            ("file",),
            ("more", "whitespace", "0", repr(item)),
            id="file wrong whitespace",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="dir_1",
                    rank=1,
                ),
            ),
            ("skip",),
            ("item", "not", "file", "directory", repr(item)),
            id="directory not exist",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 1",
                    reference_value="dir_1",
                    rank=1,
                ),
            ),
            ("dir",),
            ("more", "whitespace", "0", repr(item)),
            id="directory wrong whitespace",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="dir_1",
                    rank=1,
                    hidden=True,
                ),
            ),
            ("dir",),
            ("directory", "hidden", repr(item)),
            id="hidden directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(dir_1 := "dir_1"),
                    rank=1,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value=f"{dir_1}/file_2.md",
                    rank=2,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 3",
                    reference_value=(dir_3 := "dir_3"),
                    rank=1,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=2,
                    reference_title="title 4",
                    reference_value=f"{dir_3}/file_4.md",
                    rank=2,
                ),
            ),
            ("dir", "file", "dir", "file"),
            ("more", "whitespace", "1", repr(item)),
            id="hierarchy wrong whitespace",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="file_1.md",
                    rank=1,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value="file_2.md",
                    rank=2,
                ),
            ),
            ("file", "file"),
            ("more", "whitespace", "0", repr(item)),
            id="file wrong nesting",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(expected_dir := "dir_1"),
                    rank=1,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value="file_2.md",
                    rank=2,
                ),
            ),
            ("dir", "file"),
            ("not within", "directory", expected_dir, repr(item)),
            id="file wrong directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(expected_dir := "dir_1"),
                    rank=1,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value="dir_2",
                    rank=2,
                ),
            ),
            ("dir", "dir"),
            ("not within", "directory", expected_dir, repr(item)),
            id="directory wrong directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(value_1 := "dir_1"),
                    rank=1,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value=(value_2 := f"{value_1}/dir_2"),
                    rank=2,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 3",
                    reference_value=f"{value_1}/file_3.md",
                    rank=3,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 4",
                    reference_value=f"{value_2}/file_4.md",
                    rank=4,
                ),
            ),
            ("dir", "dir", "file", "file"),
            ("not immediately within", "directory", value_1, repr(item)),
            id="file in wrong directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(value_1 := "dir_1"),
                    rank=1,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value=(value_2 := f"{value_1}/dir_2"),
                    rank=2,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 3",
                    reference_value=f"{value_1}/file_3.md",
                    rank=3,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 4",
                    reference_value=f"{value_2}/dir_4",
                    rank=4,
                ),
            ),
            ("dir", "dir", "file", "dir"),
            ("not immediately within", "directory", value_1, repr(item)),
            id="directory in wrong directory",
        ),
    ]


@pytest.mark.parametrize(
    "parsed_items, create_paths, expected_contents",
    _test__calculate_contents_hierarchy_invalid_parameters(),
)
def test__calculate_contents_hierarchy_invalid(
    parsed_items: tuple[index._ParsedListItem, ...],
    create_paths: tuple[typing.Literal["file", "dir", "skip"], ...],
    expected_contents: tuple[str, ...],
    tmp_path: Path,
):
    """
    arrange: given the index file contents that are not valid
    act: when get_contents_list_items is called with the index file
    assert: then InputError is raised.
    """
    # Create the paths
    for parsed_item, create_path in zip(parsed_items, create_paths):
        match create_path:
            case "file":
                (tmp_path / parsed_item.reference_value).touch()
            case "dir":
                (tmp_path / parsed_item.reference_value).mkdir(parents=True)

    with pytest.raises(exceptions.InputError) as exc_info:
        tuple(index._calculate_contents_hierarchy(parsed_items=parsed_items, docs_path=tmp_path))

    assert_substrings_in_string(expected_contents, str(exc_info.value))


def test__calculate_contents_hierarchy_invalid_dir_not_in_contents(tmp_path: Path):
    """
    arrange: given the index file contents with a file in a directory that is not in the contents
    act: when get_contents_list_items is called with the index file
    assert: then InputError is raised.
    """
    (tmp_path / (value_1 := "dir_1")).mkdir()
    (tmp_path / value_1 / (value_2 := "file_2.md")).touch()
    parsed_items = (
        factories.IndexParsedListItemFactory(
            whitespace_count=0,
            reference_title="title 2",
            reference_value=f"{value_1}/{value_2}",
            rank=1,
        ),
    )

    with pytest.raises(exceptions.InputError) as exc_info:
        tuple(index._calculate_contents_hierarchy(parsed_items=parsed_items, docs_path=tmp_path))

    assert_substrings_in_string(
        ("nested item", "not", "immediately", "directory", repr(parsed_items[0])),
        str(exc_info.value),
    )


def _test__calculate_contents_hierarchy_parameters():
    """Generate parameters for the test__calculate_contents_hierarchy test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), (), id="empty"),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value := "file_1.md")
                ),
            ),
            ("file",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item.reference_title,
                    reference_value=value,
                    rank=item.rank,
                ),
            ),
            id="single file",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value := "https://canonical.com")
                ),
            ),
            ("skip",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item.reference_title,
                    reference_value=value,
                    rank=item.rank,
                ),
            ),
            id="single external link",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value := "HTTPS://canonical.com")
                ),
            ),
            ("skip",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item.reference_title,
                    reference_value=value,
                    rank=item.rank,
                ),
            ),
            id="single external link upper case",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value := "http://canonical.com")
                ),
            ),
            ("skip",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item.reference_title,
                    reference_value=value,
                    rank=item.rank,
                ),
            ),
            id="single external link http",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value := "file_1.md"), hidden=True
                ),
            ),
            ("file",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item.reference_title,
                    reference_value=value,
                    rank=item.rank,
                    hidden=True,
                ),
            ),
            id="single file hidden",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value := "file_1.MD")
                ),
            ),
            ("file",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item.reference_title,
                    reference_value=value,
                    rank=item.rank,
                ),
            ),
            id="single file upper case extension",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value := "dir_1")
                ),
            ),
            ("dir",),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item.reference_title,
                    reference_value=value,
                    rank=item.rank,
                ),
            ),
            id="single directory",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "file_1.md")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_2 := "file_2.md")
                ),
            ),
            ("file", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="multiple files",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_2 := "dir_2")
                ),
            ),
            ("dir", "dir"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="multiple directories",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_value=(value_1 := "file_1.md"),
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_value=(value_2 := "dir_2"),
                ),
            ),
            ("file", "dir"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="single file single directory",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_2 := "file_2.md")
                ),
            ),
            ("dir", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="single directory single file",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_2 := "https://canonical.com")
                ),
            ),
            ("dir", "skip"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="single directory single external link",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_2 := f"{value_1}/file_2.md")
                ),
            ),
            ("dir", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="single directory single file in directory",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_2 := "https://canonical.com")
                ),
            ),
            ("dir", "skip"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="single directory single external link",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_value=(value_2 := f"{value_1}/file_2.md")
                ),
            ),
            ("dir", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="single directory single file in directory larger whitespace",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_2 := f"{value_1}/dir_2")
                ),
            ),
            ("dir", "dir"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
            ),
            id="single directory single directory in directory",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "file_1.md")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_2 := "file_2.md")
                ),
                item_3 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_3 := "file_3.md")
                ),
            ),
            ("file", "file", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_3.reference_title,
                    reference_value=value_3,
                    rank=item_3.rank,
                ),
            ),
            id="many files",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_2 := "dir_2")
                ),
                item_3 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_3 := "dir_3")
                ),
            ),
            ("dir", "dir", "dir"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_3.reference_title,
                    reference_value=value_3,
                    rank=item_3.rank,
                ),
            ),
            id="many directories",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_2 := f"{value_1}/file_2.md")
                ),
                item_3 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_3 := "file_3.md")
                ),
            ),
            ("dir", "file", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_3.reference_title,
                    reference_value=value_3,
                    rank=item_3.rank,
                ),
            ),
            id="single file in directory",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_2 := f"{value_1}/file_2.md")
                ),
                item_3 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_3 := f"{value_1}/file_3.md")
                ),
            ),
            ("dir", "file", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_3.reference_title,
                    reference_value=value_3,
                    rank=item_3.rank,
                ),
            ),
            id="multiple files in directory",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_2 := f"{value_1}/dir_2")
                ),
                item_3 := factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_value=(value_3 := f"{value_2}/file_3.md")
                ),
            ),
            ("dir", "dir", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=3,
                    reference_title=item_3.reference_title,
                    reference_value=value_3,
                    rank=item_3.rank,
                ),
            ),
            id="single directory single nested directory single file in nested directory",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_2 := f"{value_1}/dir_2")
                ),
                item_3 := factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_value=(value_3 := f"{value_2}/dir_3")
                ),
            ),
            ("dir", "dir", "dir"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=3,
                    reference_title=item_3.reference_title,
                    reference_value=value_3,
                    rank=item_3.rank,
                ),
            ),
            id="single directory single nested directory single directory in nested directory",
        ),
        pytest.param(
            (
                item_1 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_1 := "dir_1")
                ),
                item_2 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_2 := f"{value_1}/file_2.md")
                ),
                item_3 := factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_value=(value_3 := "dir_3")
                ),
                item_4 := factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_value=(value_4 := f"{value_3}/file_4.md")
                ),
            ),
            ("dir", "file", "dir", "file"),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_1.reference_title,
                    reference_value=value_1,
                    rank=item_1.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_2.reference_title,
                    reference_value=value_2,
                    rank=item_2.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1,
                    reference_title=item_3.reference_title,
                    reference_value=value_3,
                    rank=item_3.rank,
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2,
                    reference_title=item_4.reference_title,
                    reference_value=value_4,
                    rank=item_4.rank,
                ),
            ),
            id="multiple files in multiple directories",
        ),
    ]


@pytest.mark.parametrize(
    "parsed_items, create_paths, expected_items",
    _test__calculate_contents_hierarchy_parameters(),
)
def test__calculate_contents_hierarchy(
    parsed_items: tuple[index._ParsedListItem, ...],
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
    for parsed_item, create_path in zip(parsed_items, create_paths):
        match create_path:
            case "file":
                (tmp_path / parsed_item.reference_value).touch()
            case "dir":
                (tmp_path / parsed_item.reference_value).mkdir(parents=True)

    returned_items = tuple(
        index._calculate_contents_hierarchy(parsed_items=parsed_items, docs_path=tmp_path)
    )

    assert returned_items == expected_items
