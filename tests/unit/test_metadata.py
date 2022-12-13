# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for metadata module."""

from pathlib import Path

import pytest

from src import exceptions, metadata, types_

from .helpers import assert_substrings_in_string, create_metadata_yaml


def test_get_yaml_missing(tmp_path: Path):
    """
    arrange: given empty directory
    act: when get is called with that directory
    assert: then InputError is raised.
    """
    with pytest.raises(exceptions.InputError) as exc_info:
        metadata.get(path=tmp_path)

    assert metadata.METADATA_FILENAME in str(exc_info.value).lower()


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
def test_get_yaml_malformed(
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
    "metadata_name, metadata_docs_url",
    [
        pytest.param("name", "", id="name only"),
        pytest.param("name", "https://discourse.charmhub.io/t/index/1", id="name with docs"),
    ],
)
def test_get(metadata_name: str, metadata_docs_url: str, tmp_path: Path):
    """
    arrange: given directory with metadata.yaml with valid metadata yaml
    act: when get is called with the directory
    assert: then file contents are returned as a dictionary.
    """
    metadata_docs_line = (
        f"{metadata.METADATA_DOCS_KEY}: {metadata_docs_url}\n" if metadata_docs_url else ""
    )
    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: {metadata_name}\n"
        f"{metadata_docs_line}"
        "key: value",
        path=tmp_path,
    )

    data = metadata.get(path=tmp_path)

    assert data == types_.Metadata(name=metadata_name, docs=metadata_docs_url or None)


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
    ],
)
def test_get_invalid_metadata(
    metadata_yaml_content: str, expected_error_msg_contents: tuple[str, ...], tmp_path: Path
):
    """
    arrange: given metadata with missing required keys
    act: when get is called with the directory
    assert: InputError is raised with missing keys info.
    """
    create_metadata_yaml(content=metadata_yaml_content, path=tmp_path)

    with pytest.raises(exceptions.InputError) as exc_info:
        metadata.get(path=tmp_path)

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())
