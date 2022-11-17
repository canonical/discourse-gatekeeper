# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for run module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from unittest import mock

import pytest

from src import discourse, run
from src.exceptions import DiscourseError, InputError, ServerError


def create_metadata_yaml(content: str, path: Path) -> None:
    """Create the metadata file.

    Args:
        content: The text to be written to the file.
        path: The directory to create the file in.

    """
    metadata_yaml = path / run.METADATA_FILENAME
    metadata_yaml.write_text(content, encoding="utf-8")


def assert_substrings_in_string(substrings: tuple[str, ...], string: str) -> None:
    """Assert that a string contains substrings.

    Args:
        string: The string to check.
        substrings: The sub strings that must be contained in the string.

    """
    for substring in substrings:
        assert substring in string


def test__get_metadata_metadata_yaml_missing(tmp_path: Path):
    """
    arrange: given empty directory
    act: when _get_metadata is called with that directory
    assert: then InputError is raised.
    """
    with pytest.raises(InputError) as exc_info:
        run._get_metadata(path=tmp_path)

    assert run.METADATA_FILENAME in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "metadata_yaml_content, expected_error_msg_contents",
    [
        pytest.param("", ("empty", run.METADATA_FILENAME), id="malformed"),
        pytest.param("malformed: yaml:", ("malformed", run.METADATA_FILENAME), id="malformed"),
        pytest.param("value 1", ("not", "mapping", run.METADATA_FILENAME), id="not dict"),
    ],
)
def test__get_metadata_metadata_yaml_malformed(
    metadata_yaml_content: str, expected_error_msg_contents: tuple[str, ...], tmp_path: Path
):
    """
    arrange: given directory with metadata.yaml that is malformed
    act: when _get_metadata is called with the directory
    assert: then InputError is raised.
    """
    create_metadata_yaml(content=metadata_yaml_content, path=tmp_path)

    with pytest.raises(InputError) as exc_info:
        run._get_metadata(path=tmp_path)

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())


def test__get_metadata_metadata(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml with valid mapping yaml
    act: when _get_metadata is called with the directory
    assert: then file contents are returned as a dictionary.
    """
    create_metadata_yaml(content="key: value", path=tmp_path)

    metadata = run._get_metadata(path=tmp_path)

    assert metadata == {"key": "value"}


@pytest.mark.parametrize(
    "metadata, expected_error_msg_content",
    [
        pytest.param({}, "not defined", id="empty"),
        pytest.param({"key": "value"}, "not defined", id="docs not defined"),
        pytest.param({run.METADATA_DOCS_KEY: ""}, "empty", id="docs empty"),
        pytest.param({run.METADATA_DOCS_KEY: 5}, "not a string", id="not string"),
    ],
)
def test__get_key_docs_missing_malformed(metadata: dict, expected_error_msg_content: str):
    """
    arrange: given malformed metadata
    act: when _get_key is called with the metadata
    assert: then InputError is raised.
    """
    with pytest.raises(InputError) as exc_info:
        run._get_key(metadata=metadata, key=run.METADATA_DOCS_KEY)

    assert_substrings_in_string(
        (
            f"'{run.METADATA_DOCS_KEY}'",
            expected_error_msg_content,
            run.METADATA_FILENAME,
            f"{metadata=!r}",
        ),
        str(exc_info.value).lower(),
    )


def test__get_key():
    """
    arrange: given metadata with docs key
    act: when _get_key is called with the metadata
    assert: then the docs value is returned.
    """
    docs_key = run.METADATA_DOCS_KEY
    docs_value = "url 1"

    returned_value = run._get_key(metadata={docs_key: docs_value}, key=docs_key)

    assert returned_value == docs_value


def test__read_docs_index_docs_folder_missing(tmp_path: Path):
    """
    arrange: given empty directory
    act: when _read_docs_index is called with the directory
    assert: then InputError is raised.
    """
    with pytest.raises(InputError) as exc_info:
        run._read_docs_index(base_path=tmp_path)

    assert_substrings_in_string(
        ("not", "find", "directory", str(tmp_path / run.DOCUMENTATION_FOLDER_NAME)),
        str(exc_info.value).lower(),
    )


def test__read_docs_index_index_file_missing(tmp_path: Path):
    """
    arrange: given directory with the docs folder
    act: when _read_docs_index is called with the directory
    assert: then InputError is raised.
    """
    docs_folder = tmp_path / run.DOCUMENTATION_FOLDER_NAME
    docs_folder.mkdir()

    with pytest.raises(InputError) as exc_info:
        run._read_docs_index(base_path=tmp_path)

    assert_substrings_in_string(
        ("not", "find", "file", str(docs_folder / run.DOCUMENTATION_INDEX_FILENAME)),
        str(exc_info.value).lower(),
    )


def test__read_docs_index_index_file(index_file_content: str, tmp_path: Path):
    """
    arrange: given directory with the docs folder and index file
    act: when _read_docs_index is called with the directory
    assert: then the index file content is returned.
    """
    returned_content = run._read_docs_index(base_path=tmp_path)

    assert returned_content == index_file_content


@pytest.mark.parametrize(
    "metadata_yaml_content, create_if_not_exists, expected_error_msg_contents",
    [
        pytest.param("", True, ("empty",), id="empty file"),
        pytest.param(
            "key: value",
            True,
            (
                "'name'",
                "not",
                "defined",
            ),
            id="create_if_not_exists True name not defined",
        ),
        pytest.param(
            "key: value",
            False,
            (f"'{run.METADATA_DOCS_KEY}'", "not defined", "'create_if_not_exists'", "false"),
            id="create_if_not_exists False docs not defined",
        ),
        pytest.param(
            f"{run.METADATA_DOCS_KEY}: ''",
            False,
            (f"'{run.METADATA_DOCS_KEY}'", "empty"),
            id="create_if_not_exists False docs malformed",
        ),
    ],
)
def test_retrieve_or_create_index_input_error(
    metadata_yaml_content: str,
    create_if_not_exists: bool,
    expected_error_msg_contents: tuple[str, ...],
    tmp_path: Path,
):
    """
    arrange: given directory with metadata.yaml with the given contents and create_if_not_exists
    act: when retrieve_or_create_index is called with that directory and create_if_not_exists
    assert: then InputError is raised.
    """
    create_metadata_yaml(content=metadata_yaml_content, path=tmp_path)

    with pytest.raises(InputError) as exc_info:
        run.retrieve_or_create_index(
            create_if_not_exists=create_if_not_exists,
            base_path=tmp_path,
            server_client=mock.MagicMock(),
        )

    assert_substrings_in_string(expected_error_msg_contents, str(exc_info.value).lower())


# Need the index file to exist
@pytest.mark.usefixtures("index_file_content")
def test_retrieve_or_create_index_metadata_yaml_create_discourse_error(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml without docs defined and discourse client that
        raises DiscourseError
    act: when retrieve_or_create_index is called with that directory and with create_if_not_exists
        True
    assert: then ServerError is raised.
    """
    create_metadata_yaml(content=f"{run.METADATA_NAME_KEY}: charm-name", path=tmp_path)
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.create_topic.side_effect = DiscourseError

    with pytest.raises(ServerError) as exc_info:
        run.retrieve_or_create_index(
            create_if_not_exists=True, base_path=tmp_path, server_client=mocked_server_client
        )

    assert_substrings_in_string(("index page", "creation", "failed"), str(exc_info.value).lower())


def test_retrieve_or_create_index_metadata_yaml_create(tmp_path: Path, index_file_content: str):
    """
    arrange: given directory with metadata.yaml without docs defined, discourse client that returns
        url and index file that has been created
    act: when retrieve_or_create_index is called with that directory and with create_if_not_exists
        True
    assert: then create topic is called with the titleised charm name and with placeholder content
        and the url returned by the client and placeholder content is returned.
    """
    create_metadata_yaml(content=f"{run.METADATA_NAME_KEY}: charm-name", path=tmp_path)
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    url = "http://server/index-page"
    mocked_server_client.create_topic.return_value = url

    returned_page = run.retrieve_or_create_index(
        create_if_not_exists=True, base_path=tmp_path, server_client=mocked_server_client
    )

    assert returned_page.url == url
    assert index_file_content in returned_page.content.lower()

    mocked_server_client.create_topic.assert_called_once()
    call_kwargs = mocked_server_client.create_topic.call_args.kwargs
    assert "title" in call_kwargs and "Charm Name" in call_kwargs["title"]
    assert "content" in call_kwargs and index_file_content in call_kwargs["content"]


def test_retrieve_or_create_index_metadata_yaml_retrieve_discourse_error(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml with docs defined and discourse client that
        raises DiscourseError
    act: when retrieve_or_create_index is called with that directory
    assert: then ServerError is raised.
    """
    create_metadata_yaml(
        content=f"{run.METADATA_DOCS_KEY}: http://server/index-page", path=tmp_path
    )
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.side_effect = DiscourseError

    with pytest.raises(ServerError) as exc_info:
        run.retrieve_or_create_index(
            create_if_not_exists=False,
            base_path=tmp_path,
            server_client=mocked_server_client,
        )

    assert_substrings_in_string(("index page", "retrieval", "failed"), str(exc_info.value).lower())


def test_retrieve_or_create_index_metadata_yaml_retrieve(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml with docs defined and discourse client that
        returns the index page content
    act: when retrieve_or_create_index is called with that directory
    assert: then retrieve topic is called with the docs key value and the content returned by the
        client and docs key is returned.
    """
    url = "http://server/index-page"
    content = "content 1"
    create_metadata_yaml(content=f"{run.METADATA_DOCS_KEY}: {url}", path=tmp_path)
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.return_value = content

    returned_page = run.retrieve_or_create_index(
        create_if_not_exists=False,
        base_path=tmp_path,
        server_client=mocked_server_client,
    )

    assert returned_page.url == url
    assert returned_page.content == content
    mocked_server_client.retrieve_topic.assert_called_once_with(url=url)
