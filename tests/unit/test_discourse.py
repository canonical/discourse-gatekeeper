# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for discourse."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from unittest import mock

import pydiscourse
import pydiscourse.exceptions
import pytest
import requests

from src.discourse import _URL_PATH_PREFIX, Discourse, create_discourse
from src.exceptions import DiscourseError, InputError

from . import helpers


@pytest.mark.parametrize(
    "topic_url, expected_result, expected_error_msg_contents",
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
            f"http://discourse{_URL_PATH_PREFIX}slug",
            False,
            ("unexpected", "number", "path", "components", "3", "got", "2"),
            id="1 component missing",
        ),
        pytest.param(
            f"http://discourse{_URL_PATH_PREFIX}slug/1/a",
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
            f"http://discourse{_URL_PATH_PREFIX}/1",
            False,
            ("empty", "second", "path", "component", "topic slug"),
            id="slug empty",
        ),
        pytest.param(
            f"http://discourse{_URL_PATH_PREFIX}slug/a",
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
            f"http://discourse{_URL_PATH_PREFIX}slug/1a",
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
            f"http://discourse{_URL_PATH_PREFIX}slug/1",
            True,
            None,
            id="valid",
        ),
        pytest.param(
            f"http://discourse{_URL_PATH_PREFIX}slug/1/",
            True,
            None,
            id="valid trailing /",
        ),
        pytest.param(
            f"{_URL_PATH_PREFIX}slug/1",
            True,
            None,
            id="valid no protocol host",
        ),
    ],
)
def test_topic_url_valid(
    topic_url: str,
    expected_result: bool,
    expected_error_msg_contents: tuple[str, ...],
    discourse_mocked_get_requests_session: Discourse,
):
    """
    arrange: given a topic url, expected result and expected message contents
    act: when the topic url is passed to topic_url_valid
    assert: then the expected result and message with the expected contents are returned.
    """
    discourse = discourse_mocked_get_requests_session
    # mypy complains that _get_requests_session has no attribute ..., it is actually mocked
    discourse._get_requests_session.return_value.head.return_value.url = topic_url  # type: ignore

    result = discourse.topic_url_valid(url=topic_url)

    assert result.value == expected_result, "unexpected validation result"
    if not expected_result:
        assert isinstance(result.message, str)
        assert topic_url in result.message
        for expected_message_content in expected_error_msg_contents:
            assert (
                expected_message_content in result.message.lower()
            ), "information missing from message"


@pytest.mark.parametrize(
    "function_, additional_args",
    [
        pytest.param("check_topic_write_permission", (), id="check_topic_write_permission"),
        pytest.param("check_topic_read_permission", (), id="check_topic_read_permission"),
        pytest.param("retrieve_topic", (), id="retrieve_topic"),
        pytest.param("delete_topic", (), id="delete_topic"),
        pytest.param("update_topic", ("content 1",), id="update_topic"),
    ],
)
def test_function_call_invalid_url(function_: str, additional_args: tuple, discourse: Discourse):
    """
    arrange: given an invalid topic url, name of a function and any additional arguments
    act: when the function is called with the url and any additional arguments
    assert: then DiscourseError is raised.
    """
    with pytest.raises(DiscourseError) as exc_info:
        getattr(discourse, function_)("", *additional_args)
    assert "base path" in str(exc_info.value)


@pytest.mark.parametrize(
    "function_, topic_data",
    [
        pytest.param("check_topic_write_permission", None, id="check_topic_write_permission None"),
        pytest.param(
            "check_topic_write_permission", "topic", id="check_topic_write_permission string"
        ),
        pytest.param("check_topic_write_permission", {}, id="check_topic_write_permission empty"),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": None},
            id="check_topic_write_permission post_stream None",
        ),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": {}},
            id="check_topic_write_permission post_stream posts missing",
        ),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": {"posts": None}},
            id="check_topic_write_permission post_stream posts None",
        ),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": {"posts": []}},
            id="check_topic_write_permission post_stream posts empty",
        ),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": {"posts": [None]}},
            id="check_topic_write_permission post_stream posts contains None",
        ),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": {"posts": [{}]}},
            id="check_topic_write_permission post_stream posts post empty",
        ),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": {"posts": [{"post_number": 2}]}},
            id="check_topic_write_permission post_stream posts post post_number "
            "does not include 1",
        ),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": {"posts": [{"post_number": 1}]}},
            id="check_topic_write_permission post_stream posts post user_deleted missing",
        ),
        pytest.param(
            "check_topic_write_permission",
            {"post_stream": {"posts": [{"post_number": 1, "user_deleted": False}]}},
            id="check_topic_write_permission post_stream posts post can_edit missing",
        ),
        pytest.param(
            "check_topic_write_permission",
            {
                "post_stream": {
                    "posts": [{"post_number": 1, "user_deleted": False, "can_edit": "false"}]
                }
            },
            id="check_topic_write_permission post_stream posts post can_edit not boolean",
        ),
        pytest.param("check_topic_read_permission", None, id="check_topic_read_permission None"),
    ],
)
def test_check_topic_malformed(
    monkeypatch: pytest.MonkeyPatch,
    function_: str,
    topic_data,
    discourse: Discourse,
    topic_url: str,
):
    """
    arrange: given a mocked discourse client that returns given data for a topic
    act: when given function is called
    assert: then DiscourseError is raised.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    mocked_client.topic.return_value = topic_data
    monkeypatch.setattr(discourse, "_client", mocked_client)

    with pytest.raises(DiscourseError) as exc_info:
        getattr(discourse, function_)(url=topic_url)

    exc_str = str(exc_info.value).lower()
    assert "server" in exc_str
    assert "returned" in exc_str
    assert "unexpected" in exc_str
    assert "data" in exc_str


def test_check_topic_write_permission_user_deleted(
    monkeypatch: pytest.MonkeyPatch, discourse: Discourse, topic_url: str
):
    """
    arrange: given a mocked discourse client that returns a deleted topic
    act: when check_topic_write_permission is called
    assert: then DiscourseError is raised.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    mocked_client.topic.return_value = {
        "post_stream": {"posts": [{"post_number": 1, "user_deleted": True, "can_edit": True}]}
    }
    monkeypatch.setattr(discourse, "_client", mocked_client)

    with pytest.raises(DiscourseError) as exc_info:
        discourse.check_topic_write_permission(url=topic_url)

    exc_str = str(exc_info.value).lower()
    assert "topic" in exc_str
    assert "deleted" in exc_str
    assert "url" in exc_str
    assert topic_url in exc_str


@pytest.mark.parametrize(
    "function_, topic_data, expected_return_value",
    [
        pytest.param(
            "check_topic_write_permission",
            {
                "post_stream": {
                    "posts": [{"post_number": 1, "user_deleted": False, "can_edit": False}]
                }
            },
            False,
            id="check_topic_write_permission post_stream posts post can_edit False",
        ),
        pytest.param(
            "check_topic_write_permission",
            {
                "post_stream": {
                    "posts": [{"post_number": 1, "user_deleted": False, "can_edit": True}]
                }
            },
            True,
            id="check_topic_write_permission post_stream posts post can_edit True",
        ),
        pytest.param(
            "check_topic_write_permission",
            {
                "post_stream": {
                    "posts": [
                        {"post_number": 1, "user_deleted": False, "can_edit": False},
                        {"post_number": 2, "user_deleted": False, "can_edit": True},
                    ]
                }
            },
            False,
            id="check_topic_write_permission post_stream posts multiple post first has "
            "post_number == 1",
        ),
        pytest.param(
            "check_topic_write_permission",
            {
                "post_stream": {
                    "posts": [
                        {"post_number": 2, "user_deleted": False, "can_edit": True},
                        {"post_number": 1, "user_deleted": False, "can_edit": False},
                    ]
                }
            },
            False,
            id="check_topic_write_permission post_stream posts multiple post second has "
            "post_number == 1",
        ),
        pytest.param(
            "check_topic_read_permission",
            {"post_stream": {"posts": [{"post_number": 1, "user_deleted": False}]}},
            True,
            id="check_topic_read_permission",
        ),
    ],
)
# All arguments needed to be able to parametrize tests
# pylint: disable=too-many-arguments
def test_check_topic_success(
    monkeypatch: pytest.MonkeyPatch,
    function_: str,
    topic_data,
    expected_return_value,
    discourse: Discourse,
    topic_url: str,
):
    """
    arrange: given a mocked discourse client that returns given data for a topic
    act: when given function is called
    assert: then the expected value is returned.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    mocked_client.topic.return_value = topic_data
    monkeypatch.setattr(discourse, "_client", mocked_client)

    return_value = getattr(discourse, function_)(url=topic_url)

    assert return_value == expected_return_value


@pytest.mark.parametrize(
    "post_data",
    [
        pytest.param(None, id="None"),
        pytest.param({"topic_id": 1}, id="topic_slug missing"),
        pytest.param({"topic_slug": 1, "topic_id": 1}, id="topic_slug not string"),
        pytest.param({"topic_slug": "slug"}, id="topic_id missing"),
        pytest.param({"topic_slug": "slug", "topic_id": "1"}, id="topic_id not int"),
    ],
)
def test_create_topic_post_malformed(
    monkeypatch: pytest.MonkeyPatch, post_data, discourse: Discourse
):
    """
    arrange: given a mocked discourse client that returns given data for a post
    act: when given create_topic is called
    assert: then DiscourseError is raised.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    mocked_client.create_post.return_value = post_data
    monkeypatch.setattr(discourse, "_client", mocked_client)

    with pytest.raises(DiscourseError) as exc_info:
        discourse.create_topic(title="title 1", content="content 1")

    exc_str = str(exc_info.value).lower()
    assert "server" in exc_str
    assert "returned" in exc_str
    assert "unexpected" in exc_str
    assert "data" in exc_str


def test_create_topic(monkeypatch: pytest.MonkeyPatch, base_path: str, discourse: Discourse):
    """
    arrange: given a mocked discourse client that returns valid data for a post
    act: when create_topic is called
    assert: then the url to the topic is returned.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    topic_slug = "slug"
    topic_id = 1
    post_data = {"topic_slug": topic_slug, "topic_id": topic_id}
    mocked_client.create_post.return_value = post_data
    monkeypatch.setattr(discourse, "_client", mocked_client)

    url = discourse.create_topic(title="title 1", content="content 1")

    assert url == f"{base_path}{_URL_PATH_PREFIX}{topic_slug}/{topic_id}"


def test_delete_topic(
    monkeypatch: pytest.MonkeyPatch, topic_url: str, base_path: str, discourse: Discourse
):
    """
    arrange: given a mocked discourse client
    act: when delete_topic is called first without the base path and then with it
    assert: then the url to the topic is returned.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    url_path = topic_url.removeprefix(base_path)
    monkeypatch.setattr(discourse, "_client", mocked_client)

    returned_url = discourse.delete_topic(url=url_path)

    assert returned_url == topic_url

    returned_url = discourse.delete_topic(url=topic_url)

    assert returned_url == topic_url


@pytest.mark.parametrize(
    "topic_data",
    [
        pytest.param(
            {"post_stream": {"posts": [{"post_number": 1, "user_deleted": False}]}},
            id="id missing",
        ),
        pytest.param(
            {"post_stream": {"posts": [{"post_number": 1, "user_deleted": False, "id": "1"}]}},
            id="id not integer",
        ),
    ],
)
def test_update_topic_malformed(
    monkeypatch: pytest.MonkeyPatch, topic_data, discourse: Discourse, topic_url: str
):
    """
    arrange: given a mocked discourse client that returns given data for a topic bafter it is
        updated
    act: when update_topic is called
    assert: then DiscourseError is raised.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    mocked_client.topic.return_value = topic_data
    monkeypatch.setattr(discourse, "_client", mocked_client)

    with pytest.raises(DiscourseError) as exc_info:
        discourse.update_topic(url=topic_url, content="content 1")

    exc_str = str(exc_info.value).lower()
    assert "server" in exc_str
    assert "returned" in exc_str
    assert "unexpected" in exc_str
    assert "data" in exc_str


def test_update_topic_discourse_error(
    monkeypatch: pytest.MonkeyPatch, discourse: Discourse, topic_url: str
):
    """
    arrange: given mocked discourse client that raises an error
    act: when the given update_topic is called
    assert: then DiscourseError is raised.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    mocked_client.topic.return_value = {
        "post_stream": {"posts": [{"post_number": 1, "user_deleted": False, "id": 1}]}
    }
    mocked_client.update_post.side_effect = pydiscourse.exceptions.DiscourseError
    monkeypatch.setattr(discourse, "_client", mocked_client)

    content = "content 1"
    with pytest.raises(DiscourseError) as exc_info:
        discourse.update_topic(url=topic_url, content=content)

    exc_message = str(exc_info.value).lower()
    assert "updating" in exc_message
    assert "url" in exc_message
    assert topic_url in exc_message
    assert "content" in exc_message
    assert content in exc_message


def test_update_topic(
    monkeypatch: pytest.MonkeyPatch, discourse: Discourse, base_path: str, topic_url: str
):
    """
    arrange: given a mocked discourse client that returns valid data for a topic
    act: when given update_topic is called without base path and then with
    assert: then topic url is returned.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    mocked_client.topic.return_value = {
        "post_stream": {"posts": [{"post_number": 1, "user_deleted": False, "id": 1}]}
    }
    monkeypatch.setattr(discourse, "_client", mocked_client)
    url_path = topic_url.removeprefix(base_path)

    returned_url = discourse.update_topic(url=url_path, content="content 1")

    assert returned_url == topic_url

    returned_url = discourse.update_topic(url=topic_url, content="content 1")

    assert returned_url == topic_url


@pytest.mark.parametrize(
    "client_function, function_, kwargs, expected_error_msg_contents",
    [
        pytest.param(
            "topic",
            "check_topic_write_permission",
            {"url": helpers.get_discourse_topic_url()},
            ("retrieving", "url", helpers.get_discourse_topic_url()),
            id="check_topic_write_permission",
        ),
        pytest.param(
            "topic",
            "check_topic_read_permission",
            {"url": helpers.get_discourse_topic_url()},
            ("retrieving", "url", helpers.get_discourse_topic_url()),
            id="check_topic_read_permission",
        ),
        pytest.param(
            "create_post",
            "create_topic",
            {"title": "title 1", "content": "content 1"},
            ("creating", "title", "title 1", "content", "content 1"),
            id="create_topic",
        ),
        pytest.param(
            "delete_topic",
            "delete_topic",
            {"url": helpers.get_discourse_topic_url()},
            ("deleting", "url", helpers.get_discourse_topic_url()),
            id="delete_topic",
        ),
    ],
)
# All arguments needed to be able to parametrize tests
@pytest.mark.usefixtures("topic_url")
def test_function_discourse_error(
    monkeypatch: pytest.MonkeyPatch,
    client_function: str,
    function_: str,
    kwargs: dict,
    expected_error_msg_contents: tuple[str, ...],
    discourse: Discourse,
):  # pylint: disable=too-many-arguments
    """
    arrange: given mocked discourse client that raises an error
    act: when the given function is called
    assert: then DiscourseError is raised.
    """
    mocked_client = mock.MagicMock(spec=pydiscourse.DiscourseClient)
    getattr(mocked_client, client_function).side_effect = pydiscourse.exceptions.DiscourseError
    monkeypatch.setattr(discourse, "_client", mocked_client)

    with pytest.raises(DiscourseError) as exc_info:
        getattr(discourse, function_)(**kwargs)

    exc_message = str(exc_info.value).lower()
    for expected_message_content in expected_error_msg_contents:
        assert expected_message_content in exc_message


def test_retrieve_topic_read_error(
    monkeypatch: pytest.MonkeyPatch, discourse: Discourse, topic_url: str
):
    """
    arrange: given mocked check_topic_read_permission that returns False
    act: when retrieve_topic is called
    assert: then DiscourseError is raised.
    """
    mocked_check_topic_read_permission = mock.MagicMock(spec=Discourse.check_topic_read_permission)
    mocked_check_topic_read_permission.return_value = False
    monkeypatch.setattr(
        discourse, "check_topic_read_permission", mocked_check_topic_read_permission
    )

    with pytest.raises(DiscourseError) as exc_info:
        discourse.retrieve_topic(url=topic_url)

    exc_message = str(exc_info.value).lower()
    assert "retrieving" in exc_message
    assert "url" in exc_message
    assert topic_url in exc_message


def test_retrieve_topic_head_http_error(
    monkeypatch: pytest.MonkeyPatch,
    discourse_mocked_get_requests_session: Discourse,
    topic_url: str,
):
    """
    arrange: given mocked requests that raises a HTTPError on a head request
    act: when retrieve_topic is called
    assert: then DiscourseError is raised.
    """
    discourse = discourse_mocked_get_requests_session
    mocked_check_topic_read_permission = mock.MagicMock(spec=Discourse.check_topic_read_permission)
    mocked_check_topic_read_permission.return_value = True
    monkeypatch.setattr(
        discourse, "check_topic_read_permission", mocked_check_topic_read_permission
    )
    # mypy complains that _get_requests_session has no attribute ..., it is actually mocked
    mocked_head = discourse._get_requests_session.return_value.head  # type: ignore
    mocked_head.return_value.raise_for_status.side_effect = requests.HTTPError

    with pytest.raises(DiscourseError) as exc_info:
        discourse.retrieve_topic(url=topic_url)

    exc_message = str(exc_info.value).lower()
    assert "resolved" in exc_message
    assert "url" in exc_message
    assert topic_url in exc_message


def test_retrieve_topic_get_http_error(
    monkeypatch: pytest.MonkeyPatch,
    discourse: Discourse,
    topic_url: str,
):
    """
    arrange: given mocked requests that raises a HTTPError on a get request
    act: when retrieve_topic is called
    assert: then DiscourseError is raised.
    """
    mocked_check_topic_read_permission = mock.MagicMock(spec=Discourse.check_topic_read_permission)
    mocked_check_topic_read_permission.return_value = True
    monkeypatch.setattr(
        discourse, "check_topic_read_permission", mocked_check_topic_read_permission
    )
    # mypy complains that _get_requests_session has no attribute ..., it is actually mocked
    mocked_get = discourse._get_requests_session.return_value.get  # type: ignore
    mocked_get.return_value.raise_for_status.side_effect = requests.HTTPError

    with pytest.raises(DiscourseError) as exc_info:
        discourse.retrieve_topic(url=topic_url)

    exc_message = str(exc_info.value).lower()
    assert "retrieving" in exc_message
    assert "url" in exc_message
    assert topic_url in exc_message


def test_retrieve_topic(
    monkeypatch: pytest.MonkeyPatch,
    discourse_mocked_get_requests_session: Discourse,
    base_path: str,
    topic_url: str,
):
    """
    arrange: given mocked requests that returns content
    act: when retrieve_topic is called
    assert: then the content is returned.
    """
    discourse = discourse_mocked_get_requests_session
    mocked_check_topic_read_permission = mock.MagicMock(spec=Discourse.check_topic_read_permission)
    mocked_check_topic_read_permission.return_value = True
    monkeypatch.setattr(
        discourse, "check_topic_read_permission", mocked_check_topic_read_permission
    )
    content = "content 1"
    # mypy complains that _get_requests_session has no attribute ..., it is actually mocked
    mocked_get = discourse._get_requests_session.return_value.get  # type: ignore
    mocked_get.return_value.content = content.encode(encoding="utf-8")

    returned_content = discourse.retrieve_topic(url=topic_url)

    assert returned_content == content

    url_path = topic_url.removeprefix(base_path)
    returned_content = discourse.retrieve_topic(url=url_path)

    assert returned_content == content


def test_absolute_url(topic_url: str, base_path: str, discourse: Discourse):
    """
    arrange: given a mocked discourse client
    act: when absolute_url is called first without the base path and then with it
    assert: then the url to the topic is returned.
    """
    url_path = topic_url.removeprefix(base_path)

    returned_url = discourse.absolute_url(url=url_path)

    assert returned_url == topic_url

    returned_url = discourse.absolute_url(url=topic_url)

    assert returned_url == topic_url


@pytest.mark.parametrize(
    "kwargs, expected_error_msg_contents",
    [
        pytest.param(
            {"hostname": "", "category_id": "1", "api_username": "user 1", "api_key": "key 1"},
            ("invalid", "'discourse_host'", "empty", f"{''!r}"),
            id="hostname empty",
        ),
        pytest.param(
            {
                "hostname": "http://discourse",
                "category_id": "1",
                "api_username": "user 1",
                "api_key": "key 1",
            },
            ("invalid", "'discourse_host'", "http://discourse"),
            id="hostname has http",
        ),
        pytest.param(
            {
                "hostname": "HTTP://discourse",
                "category_id": "1",
                "api_username": "user 1",
                "api_key": "key 1",
            },
            ("invalid", "'discourse_host'", "HTTP://discourse"),
            id="hostname has HTTP",
        ),
        pytest.param(
            {
                "hostname": "https://discourse",
                "category_id": "1",
                "api_username": "user 1",
                "api_key": "key 1",
            },
            ("invalid", "'discourse_host'", "https://discourse"),
            id="hostname has https",
        ),
        pytest.param(
            {
                "hostname": "discourse",
                "category_id": "",
                "api_username": "user 1",
                "api_key": "key 1",
            },
            ("invalid", "'discourse_category_id'", "it must be non-empty"),
            id="empty category_id",
        ),
        pytest.param(
            {
                "hostname": "discourse",
                "category_id": "not an integer",
                "api_username": "user 1",
                "api_key": "key 1",
            },
            ("invalid", "'discourse_category_id'", "integer", f"{'not an integer'!r}"),
            id="category_id str that is not convertible to int",
        ),
        pytest.param(
            {"hostname": "discourse", "category_id": "1", "api_username": "", "api_key": "key 1"},
            ("empty", "'discourse_api_username'", f"{''!r}"),
            id="api_username empty",
        ),
        pytest.param(
            {"hostname": "discourse", "category_id": "1", "api_username": "user 1", "api_key": ""},
            ("empty", "'discourse_api_key'", f"{''!r}"),
            id="api_key empty",
        ),
    ],
)
def test_create_discourse_error(kwargs: dict, expected_error_msg_contents: tuple[str, ...]):
    """
    arrange: given invalid kwargs
    act: when create_discourse is called with the kwargs
    assert: then InputError is raised.
    """
    with pytest.raises(InputError) as exc_info:
        create_discourse(**kwargs)

    exc_message = str(exc_info.value).lower()
    for expected_message_content in expected_error_msg_contents:
        assert expected_message_content.lower() in exc_message


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param(
            {
                "hostname": "discourse",
                "category_id": "1",
                "api_username": "user 1",
                "api_key": "key 1",
            },
            id="category_id string that is convertible to an integer",
        ),
    ],
)
def test_create_discourse(kwargs: dict):
    """
    arrange: given kwargs
    act: when create_discourse is called with the kwargs
    assert: then a Discourse instance is returned.
    """
    discourse = create_discourse(**kwargs)

    assert isinstance(discourse, Discourse)
