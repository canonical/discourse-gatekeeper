# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for discourse."""

import pytest

from src.discourse import Discourse, DiscourseError


@pytest.mark.parametrize(
    "topic_url, expected_result, expected_message_contents",
    [
        pytest.param(
            "", False, ("different", "base path", "expected", "http://discourse"), id="empty"
        ),
        pytest.param(
            "http://discourse",
            False,
            ("unexpected", "number", "path", "components", "3", "got", "0"),
            id="all components missing",
        ),
        pytest.param(
            "http://discourse/t",
            False,
            ("unexpected", "number", "path", "components", "3", "got", "1"),
            id="2 components missing",
        ),
        pytest.param(
            "http://discourse/t/slug",
            False,
            ("unexpected", "number", "path", "components", "3", "got", "2"),
            id="1 component missing",
        ),
        pytest.param(
            "http://discourse/t/slug/1/a",
            False,
            ("unexpected", "number", "path", "components", "expected", "3", "got", "4"),
            id="too many components",
        ),
        pytest.param(
            "http://discourse//slug/1",
            False,
            ("unexpected", "first", "path", "component", "expected", "t", "got", ""),
            id="first component wrong no character",
        ),
        pytest.param(
            "http://discourse/a/slug/1",
            False,
            ("unexpected", "first", "path", "component", "expected", "t", "got", "a"),
            id="first component wrong single character",
        ),
        pytest.param(
            "http://discourse/ab/slug/1",
            False,
            ("unexpected", "first", "path", "component", "expected", "t", "got", "ab"),
            id="first component wrong multi character",
        ),
        pytest.param(
            "http://discourse/t//1",
            False,
            ("empty", "second", "path", "component", "topic slug"),
            id="slug empty",
        ),
        pytest.param(
            "http://discourse/t/slug/a",
            False,
            (
                "unexpected",
                "third",
                "path",
                "component",
                "topic id",
                "expected",
                "integer",
                "got",
                "a",
            ),
            id="topic id wrong character",
        ),
        pytest.param(
            "http://discourse/t/slug/1a",
            False,
            (
                "unexpected",
                "third",
                "path",
                "component",
                "topic id",
                "expected",
                "integer",
                "got",
                "1a",
            ),
            id="topic id wrong integer and character",
        ),
        pytest.param(
            "http://discourse/t/slug/1",
            True,
            None,
            id="valid",
        ),
        pytest.param(
            "http://discourse/t/slug/1/",
            True,
            None,
            id="valid trailing /",
        ),
    ],
)
def test_topic_url_valid(
    topic_url: str, expected_result: bool, expected_message_contents: tuple[str, ...]
):
    """
    arrange: given a topic url, expected result and expected message contents
    act: when the topic url is passed to topic_url_valid
    assert: then the expected result and message with the expected contents are returned.
    """
    base_path = "http://discourse"
    discourse = Discourse(base_path=base_path, api_username="", api_key="", category_id=0)

    result = discourse.topic_url_valid(url=topic_url)

    assert result.value == expected_result, "unexpected validation result"
    if not expected_result:
        assert isinstance(result.message, str)
        assert topic_url in result.message
        for expected_message_content in expected_message_contents:
            assert (
                expected_message_content in result.message.lower()
            ), "information missing from message"


@pytest.mark.parametrize(
    "function, additional_args",
    [
        pytest.param("check_topic_write_permission", (), id="check_topic_write_permission"),
        pytest.param("check_topic_read_permission", (), id="check_topic_read_permission"),
        pytest.param("retrieve_topic", (), id="retrieve_topic"),
        pytest.param("delete_topic", (), id="delete_topic"),
        pytest.param("update_topic", ("content 1",), id="update_topic"),
    ],
)
def test_function_call_invalid_url(function: str, additional_args: tuple):
    """
    arrange: given an invalid topic url, name of a function and any additional arguments
    act: when the function is called with the url and any additional arguments
    assert: then DiscourseError is raised.
    """
    discourse = Discourse(base_path="http://discourse", api_username="", api_key="", category_id=0)

    with pytest.raises(DiscourseError) as exc_info:
        getattr(discourse, function)("", *additional_args)
    assert "base path" in str(exc_info.value)
