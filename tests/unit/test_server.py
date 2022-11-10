# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for src module."""

from unittest import mock
from pathlib import Path

import pytest

from src import server
from src import discourse
from src.exceptions import InputError, DiscourseError, ServerError


def assert_string_contains_substrings(substrings: tuple[str, ...], string: str) -> None:
    """Assert that a string contains substrings.

    Args:
        string: The string to check.
        substrings: The sub strings that must be contained in the string.

    """
    for substring in substrings:
        assert substring in string


def test_retrieve_or_create_index_metadata_yaml_missing(tmp_path: Path):
    """
    arrange: given empty directory
    act: when retrieve_or_create_index is called with that directory
    assert: then InputError is raised.
    """
    with pytest.raises(InputError) as exc_info:
        server.retrieve_or_create_index(
            create_if_not_exists=False, local_base_path=tmp_path, server_client=mock.MagicMock()
        )

    assert_string_contains_substrings(("metadata.yaml",), str(exc_info.value).lower())


def test_retrieve_or_create_index_metadata_yaml_malformed(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml that is malformed
    act: when retrieve_or_create_index is called with that directory
    assert: then InputError is raised.
    """
    metadata_yaml_path = tmp_path / "metadata.yaml"
    with metadata_yaml_path.open("w", encoding="utf-8") as metadata_yaml_file:
        metadata_yaml_file.write("malformed: yaml:")

    with pytest.raises(InputError) as exc_info:
        server.retrieve_or_create_index(
            create_if_not_exists=False, local_base_path=tmp_path, server_client=mock.MagicMock()
        )

    assert_string_contains_substrings(("malformed", "metadata.yaml"), str(exc_info.value).lower())


@pytest.mark.parametrize(
    "metadata_yaml_contents",
    [
        pytest.param("", id="empty file"),
        pytest.param("key: value", id="docs not defined"),
        pytest.param("docs:", id="docs empty"),
        pytest.param("docs: 5", id="docs not string"),
    ],
)
def test_retrieve_or_create_index_metadata_yaml_docs_missing_malformed(
    tmp_path: Path, metadata_yaml_contents: str
):
    """
    arrange: given directory with metadata.yaml with the given contents
    act: when retrieve_or_create_index is called with that directory and with create_if_not_exists
        False
    assert: then InputError is raised.
    """
    metadata_yaml_path = tmp_path / "metadata.yaml"
    with metadata_yaml_path.open("w", encoding="utf-8") as metadata_yaml_file:
        metadata_yaml_file.write(metadata_yaml_contents)

    with pytest.raises(InputError) as exc_info:
        server.retrieve_or_create_index(
            create_if_not_exists=False, local_base_path=tmp_path, server_client=mock.MagicMock()
        )

    assert_string_contains_substrings(
        (
            "docs key",
            "not defined",
            "empty",
            "not a string",
            "metadata.yaml",
            "creation",
            "disabled",
        ),
        str(exc_info.value).lower(),
    )


@pytest.mark.parametrize(
    "metadata_yaml_contents",
    [
        pytest.param("", id="empty file"),
        pytest.param("key: value", id="name not defined"),
        pytest.param("name:", id="name empty"),
        pytest.param("name: 5", id="name not string"),
    ],
)
def test_retrieve_or_create_index_metadata_yaml_create_name_missing_malformed(
    tmp_path: Path, metadata_yaml_contents: str
):
    """
    arrange: given directory with metadata.yaml with the given contents that does not have the docs
        key defined
    act: when retrieve_or_create_index is called with that directory and with create_if_not_exists
        True
    assert: then InputError is raised.
    """
    metadata_yaml_path = tmp_path / "metadata.yaml"
    with metadata_yaml_path.open("w", encoding="utf-8") as metadata_yaml_file:
        metadata_yaml_file.write(metadata_yaml_contents)

    with pytest.raises(InputError) as exc_info:
        server.retrieve_or_create_index(
            create_if_not_exists=True, local_base_path=tmp_path, server_client=mock.MagicMock()
        )

    assert_string_contains_substrings(
        ("name key", "not defined", "empty", "not a string", "metadata.yaml"),
        str(exc_info.value).lower(),
    )


def test_retrieve_or_create_index_metadata_yaml_create_discourse_error(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml without docs defined and discourse client that
        raises DiscourseError
    act: when retrieve_or_create_index is called with that directory and with create_if_not_exists
        True
    assert: then ServerError is raised.
    """
    metadata_yaml_path = tmp_path / "metadata.yaml"
    with metadata_yaml_path.open("w", encoding="utf-8") as metadata_yaml_file:
        metadata_yaml_file.write("name: charm-name")
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.create_topic.side_effect = DiscourseError

    with pytest.raises(ServerError) as exc_info:
        server.retrieve_or_create_index(
            create_if_not_exists=True, local_base_path=tmp_path, server_client=mocked_server_client
        )

    assert_string_contains_substrings(
        ("index page", "creation", "failed"), str(exc_info.value).lower()
    )


def test_retrieve_or_create_index_metadata_yaml_create(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml without docs defined and discourse client that
        returns url
    act: when retrieve_or_create_index is called with that directory and with create_if_not_exists
        True
    assert: then create topic is called with the titleised charm name and with placeholder contant
        and the url returned by the client and placeholder content is returned.
    """
    metadata_yaml_path = tmp_path / "metadata.yaml"
    with metadata_yaml_path.open("w", encoding="utf-8") as metadata_yaml_file:
        metadata_yaml_file.write("name: charm-name")
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    url = "http://server/index-page"
    mocked_server_client.create_topic.return_value = url

    returned_page = server.retrieve_or_create_index(
        create_if_not_exists=True, local_base_path=tmp_path, server_client=mocked_server_client
    )

    assert returned_page.url == url
    assert "placeholder" in returned_page.content.lower()

    mocked_server_client.create_topic.assert_called_once()
    call_kwargs = mocked_server_client.create_topic.call_args.kwargs
    assert "title" in call_kwargs and "Charm Name" in call_kwargs["title"]
    assert "content" in call_kwargs and "placeholder" in call_kwargs["content"]


def test_retrieve_or_create_index_metadata_yaml_retrieve_discourse_error(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml with docs defined and discourse client that
        raises DiscourseError
    act: when retrieve_or_create_index is called with that directory
    assert: then ServerError is raised.
    """
    metadata_yaml_path = tmp_path / "metadata.yaml"
    with metadata_yaml_path.open("w", encoding="utf-8") as metadata_yaml_file:
        metadata_yaml_file.write("docs: http://server/index-page")
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.side_effect = DiscourseError

    with pytest.raises(ServerError) as exc_info:
        server.retrieve_or_create_index(
            create_if_not_exists=False,
            local_base_path=tmp_path,
            server_client=mocked_server_client,
        )

    assert_string_contains_substrings(
        ("index page", "retrieval", "failed"), str(exc_info.value).lower()
    )


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
    metadata_yaml_path = tmp_path / "metadata.yaml"
    with metadata_yaml_path.open("w", encoding="utf-8") as metadata_yaml_file:
        metadata_yaml_file.write(f"docs: {url}")
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.return_value = content

    returned_page = server.retrieve_or_create_index(
        create_if_not_exists=False,
        local_base_path=tmp_path,
        server_client=mocked_server_client,
    )

    assert returned_page.url == url
    assert returned_page.content == content
    mocked_server_client.retrieve_topic.assert_called_once_with(url=url)
