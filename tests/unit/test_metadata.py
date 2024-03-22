# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for metadata module."""

from pathlib import Path

import pytest

from src import exceptions, metadata, types_

from .helpers import assert_substrings_in_string, create_charmcraft_yaml, create_metadata_yaml


def test_get_yaml_missing(tmp_path: Path):
    """
    arrange: given empty directory
    act: when get is called with that directory
    assert: then InputError is raised.
    """
    with pytest.raises(exceptions.InputError) as exc_info:
        metadata.get(path=tmp_path)

    assert metadata.METADATA_FILENAME in str(exc_info.value).lower()
    assert metadata.CHARMCRAFT_FILENAME in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "metadata_yaml_content, expected_error_msg_contents",
    [
        pytest.param("", ("empty", metadata.METADATA_FILENAME), id="malformed"),
        pytest.param(
            "malformed: yaml:", ("malformed", metadata.METADATA_FILENAME), id="malformed"
        ),
        pytest.param("value 1", ("not", "mapping", metadata.METADATA_FILENAME), id="not dict"),
    ],
)
def test_get_metadata_yaml_malformed(
    metadata_yaml_content: str, expected_error_msg_contents: tuple[str, ...], tmp_path: Path
):
    """
    arrange: given directory with metadata.yaml that is malformed
    act: when get is called with the directory
    assert: then InputError is raised.
    """
    create_metadata_yaml(content=metadata_yaml_content, path=tmp_path)

    with pytest.raises(exceptions.InputError) as exc_info:
        metadata.get(path=tmp_path)

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())


@pytest.mark.parametrize(
    "metadata_yaml_content, expected_error_msg_contents",
    [
        pytest.param("key: value", ("could not find", metadata.METADATA_NAME_KEY)),
        pytest.param(
            f"{metadata.METADATA_NAME_KEY}: 1",
            (
                "invalid value for",
                metadata.METADATA_NAME_KEY,
            ),
        ),
        pytest.param(
            f"{metadata.METADATA_NAME_KEY}: name\n{metadata.METADATA_DOCS_KEY}: 1",
            ("invalid value for", metadata.METADATA_DOCS_KEY),
        ),
        pytest.param(
            f"{metadata.METADATA_NAME_KEY}: name\n{metadata.METADATA_DOCS_KEY}: ",
            ("invalid value for", metadata.METADATA_DOCS_KEY),
        ),
    ],
)
def test_get_invalid_metadata(
    metadata_yaml_content: str, expected_error_msg_contents: tuple[str, ...], tmp_path: Path
):
    """
    arrange: given metadata with missing required keys or invalid value
    act: when get is called with the directory
    assert: InputError is raised with missing keys info.
    """
    create_metadata_yaml(content=metadata_yaml_content, path=tmp_path)

    with pytest.raises(exceptions.InputError) as exc_info:
        metadata.get(path=tmp_path)

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())


# pylint currently does not understand walrus operator perfectly yet
# pylint: disable=unused-variable,undefined-variable
@pytest.mark.parametrize(
    "metadata_yaml_content, expected_metadata",
    [
        pytest.param(
            f"{metadata.METADATA_NAME_KEY}: {(name := 'name')}",
            types_.Metadata(name=name, docs=None),
            id="name only",
        ),
        pytest.param(
            f"{metadata.METADATA_NAME_KEY}: {name}\n"
            f"{metadata.METADATA_DOCS_KEY}: "
            f"{(docs := 'https://discourse.charmhub.io/t/index/1')}",
            types_.Metadata(name=name, docs=docs),
            id="name and docs",
        ),
    ],
)
def test_get_metadata(
    metadata_yaml_content: str,
    expected_metadata: types_.Metadata,
    tmp_path: Path,
):
    """
    arrange: given directory with metadata.yaml with valid metadata yaml
    act: when get is called with the directory
    assert: then file contents are returned as a dictionary.
    """
    create_metadata_yaml(
        content=metadata_yaml_content,
        path=tmp_path,
    )

    data = metadata.get(path=tmp_path)

    assert data == expected_metadata


@pytest.mark.parametrize(
    "charmcraft_yaml_content, expected_error_msg_contents",
    [
        pytest.param("", ("empty", metadata.CHARMCRAFT_FILENAME), id="malformed"),
        pytest.param(
            "malformed: yaml:", ("malformed", metadata.CHARMCRAFT_FILENAME), id="malformed"
        ),
        pytest.param("value 1", ("not", "mapping", metadata.CHARMCRAFT_FILENAME), id="not dict"),
    ],
)
def test_get_charmcraft_yaml_malformed(
    charmcraft_yaml_content: str, expected_error_msg_contents: tuple[str, ...], tmp_path: Path
):
    """
    arrange: given directory with charmcraft.yaml that is malformed
    act: when get is called with the directory
    assert: then InputError is raised.
    """
    create_charmcraft_yaml(content=charmcraft_yaml_content, path=tmp_path)

    with pytest.raises(exceptions.InputError) as exc_info:
        metadata.get(path=tmp_path)

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())


@pytest.mark.parametrize(
    "charmcraft_yaml_content, expected_error_msg_contents",
    [
        pytest.param("key: value", ("could not find", metadata.CHARMCRAFT_NAME_KEY)),
        pytest.param(
            f"{metadata.CHARMCRAFT_NAME_KEY}: 1",
            (
                "invalid value for",
                metadata.CHARMCRAFT_NAME_KEY,
            ),
        ),
        pytest.param(
            f"{metadata.CHARMCRAFT_NAME_KEY}: name\n{metadata.CHARMCRAFT_LINKS_KEY}: 1",
            ("invalid value for", metadata.CHARMCRAFT_LINKS_KEY),
        ),
        pytest.param(
            (
                f"{metadata.CHARMCRAFT_NAME_KEY}: name\n"
                f"{metadata.CHARMCRAFT_LINKS_KEY}:\n {metadata.CHARMCRAFT_LINKS_DOCS_KEY}: 1"
            ),
            ("invalid value for", metadata.CHARMCRAFT_LINKS_DOCS_KEY),
        ),
    ],
)
def test_get_invalid_charmcraft(
    charmcraft_yaml_content: str, expected_error_msg_contents: tuple[str, ...], tmp_path: Path
):
    """
    arrange: given charmcraft with missing required keys or invalid value
    act: when get is called with the directory
    assert: InputError is raised with missing keys info.
    """
    create_charmcraft_yaml(content=charmcraft_yaml_content, path=tmp_path)

    with pytest.raises(exceptions.InputError) as exc_info:
        metadata.get(path=tmp_path)

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())


# pylint currently does not understand walrus operator perfectly yet
# pylint: disable=unused-variable,undefined-variable
@pytest.mark.parametrize(
    "charmcraft_yaml_content, expected_metadata",
    [
        pytest.param(
            f"{metadata.CHARMCRAFT_NAME_KEY}: {(name := 'name')}",
            types_.Metadata(name=name, docs=None),
            id="name only",
        ),
        pytest.param(
            f"{metadata.CHARMCRAFT_NAME_KEY}: {name}\n"
            f"{metadata.CHARMCRAFT_LINKS_KEY}:\n"
            f"  {metadata.CHARMCRAFT_LINKS_DOCS_KEY}: "
            f"{(docs := 'https://discourse.charmhub.io/t/index/1')}",
            types_.Metadata(name=name, docs=docs),
            id="name and docs",
        ),
    ],
)
def test_get_charmcraft(
    charmcraft_yaml_content: str,
    expected_metadata: types_.Metadata,
    tmp_path: Path,
):
    """
    arrange: given directory with metadata.yaml with valid metadata yaml
    act: when get is called with the directory
    assert: then file contents are returned as a dictionary.
    """
    create_charmcraft_yaml(
        content=charmcraft_yaml_content,
        path=tmp_path,
    )

    data = metadata.get(path=tmp_path)

    assert data == expected_metadata
