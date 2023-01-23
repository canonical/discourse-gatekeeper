# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for discourse."""

import re
from urllib import parse

import pydiscourse
import pytest

from src.discourse import Discourse
from src.exceptions import DiscourseError

from . import types

pytestmark = pytest.mark.discourse


SLUG_REGEX = r"\/t\/[\w-]+\/"


def change_url_slug(url: str, new_slug: str) -> str:
    """Change the slug of a topic URL.

    Args:
        url: The topic URL to change.
        new_slug: The slug to change to.

    Returns:
        The URL with the changed slug.
    """
    return re.sub(SLUG_REGEX, f"/t/{new_slug}/", url)


def remove_url_slug(url: str) -> str:
    """Remove the slug from a topic URL.

    Args:
        url: The topic URL to change.

    Returns:
        The URL without the slug.
    """
    return re.sub(SLUG_REGEX, "/t/", url)


def remove_url_topic_id(url: str) -> str:
    """Remove the topic id from a topic URL.

    Args:
        url: The topic URL to change.

    Returns:
        The URL without the topic id.
    """
    return re.sub(r"\/\d+$", "", url)


@pytest.mark.asyncio
async def test_create_retrieve_update_delete_topic(
    discourse_category_id: int,
    discourse_client: pydiscourse.DiscourseClient,
    discourse_api: Discourse,
):
    """
    arrange: given running discourse server
    act: when a topic is created, checked for permissions, retrieved, updated and deleted
    assert: then all the sequential actions succeed and the topic is deleted in the end.
    """
    # Create topic
    title = "title 1 padding so it is long enough test_crud_topic"
    content_1 = "content 1 padding so it is long enough test_crud_topic"

    url = discourse_api.create_topic(title=title, content=content_1)
    returned_content = discourse_api.retrieve_topic(url=url)

    assert returned_content == content_1, "post was created with the wrong content"
    # Check that the category is correct
    url_path_components = parse.urlparse(url=url).path.split("/")
    slug = url_path_components[-2]
    topic_id = url_path_components[-1]
    topic = discourse_client.topic(slug=slug, topic_id=topic_id)
    assert (
        topic["category_id"] == discourse_category_id
    ), "post was not created with the correct category id"
    assert topic["visible"] is False, "topic is listed"

    # Check permissions
    assert discourse_api.check_topic_read_permission(
        url=url
    ), "user could not read topic they created"
    assert discourse_api.check_topic_write_permission(
        url=url
    ), "user could not write topic they created"

    # Update topic
    content_2 = "content 2 padding so it is long enough  test_crud_topic"
    discourse_api.update_topic(url=url, content=content_2)
    returned_content = discourse_api.retrieve_topic(url=url)

    assert returned_content == content_2, "content was not updated"

    # Delete topic
    discourse_api.delete_topic(url=url)

    topic = discourse_client.topic(slug=slug, topic_id=topic_id)
    assert "withdrawn" in topic["post_stream"]["posts"][0]["cooked"], "topic not deleted"
    assert topic["post_stream"]["posts"][0]["user_deleted"], "topic not deleted"

    with pytest.raises(DiscourseError):
        discourse_api.retrieve_topic(url=url)


@pytest.mark.asyncio
async def test_retrieve_wrong_url(discourse_api: Discourse):
    """
    arrange: given running discourse server
    act: when a topic is created and retrieved with the wrong slug, without the slug or without the
        topic id
    assert: then the correct content is returned.
    """
    title = "title 1 padding so it is long enough test_retrieve_wrong_slug"
    content = "content 1 padding so it is long enough test_retrieve_wrong_slug"
    url = discourse_api.create_topic(title=title, content=content)

    url_incorrect_slug = change_url_slug(url, "wrong-slug")
    returned_content = discourse_api.retrieve_topic(url=url_incorrect_slug)

    assert returned_content == content

    url_missing_slug = remove_url_slug(url)
    returned_content = discourse_api.retrieve_topic(url=url_missing_slug)

    assert returned_content == content

    url_missing_topic_id = remove_url_topic_id(url)
    returned_content = discourse_api.retrieve_topic(url=url_missing_topic_id)

    assert returned_content == content


@pytest.mark.asyncio
async def test_update_wrong_slug(discourse_api: Discourse):
    """
    arrange: given running discourse server
    act: when a topic is created and updated with the wrong slug
    assert: then the topic is updated.
    """
    title = "title 1 padding so it is long enough test_update_wrong_slug"
    content_1 = "content 1 padding so it is long enough test_update_wrong_slug"
    url = discourse_api.create_topic(title=title, content=content_1)

    url_incorrect_slug = change_url_slug(url, "wrong-slug")
    content_2 = "content 2 padding so it is long enough test_update_wrong_slug"
    discourse_api.update_topic(url=url_incorrect_slug, content=content_2)

    returned_content = discourse_api.retrieve_topic(url=url)
    assert returned_content == content_2


@pytest.mark.asyncio
async def test_delete_wrong_slug(discourse_api: Discourse):
    """
    arrange: given running discourse server
    act: when a topic is created and deleted with the wrong slug
    assert: then the topic is deleted.
    """
    title = "title 1 padding so it is long enough test_delete_wrong_slug"
    content = "content 1 padding so it is long enough test_delete_wrong_slug"
    url = discourse_api.create_topic(title=title, content=content)

    url_incorrect_slug = change_url_slug(url, "wrong-slug")
    discourse_api.delete_topic(url=url_incorrect_slug)

    with pytest.raises(DiscourseError):
        discourse_api.retrieve_topic(url=url)


# Keep the API key parameter to ensure that the API key is created just that the wrong one is being
# used
@pytest.mark.usefixtures("discourse_user_api_key")
@pytest.mark.asyncio
async def test_create_topic_auth_error(
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
):
    """
    arrange: given running discourse server
    act: when a topic is created with an incorrect API key
    assert: then DiscourseError is raised.
    """
    discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key="invalid key",
        category_id=discourse_category_id,
    )

    # Create topic
    title = "title 1 padding so it is long enough test_create_topic_auth_error"
    content_1 = "content 1 padding so it is long enough test_create_topic_auth_error"

    with pytest.raises(DiscourseError):
        discourse.create_topic(title=title, content=content_1)


@pytest.mark.asyncio
async def test_retrieve_topic_auth_error(
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
    discourse_api: Discourse,
):
    """
    arrange: given running discourse server
    act: when a topic is created and then retrieved with an incorrect API key
    assert: then DiscourseError is raised.
    """
    title = "title 1 padding so it is long enough test_retrieve_topic_auth_error"
    content_1 = "content 1 padding so it is long enough test_retrieve_topic_auth_error"

    url = discourse_api.create_topic(title=title, content=content_1)

    unauth_discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key="invalid key",
        category_id=discourse_category_id,
    )

    with pytest.raises(DiscourseError):
        unauth_discourse.retrieve_topic(url=url)


@pytest.mark.asyncio
async def test_update_topic_auth_error(
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
    discourse_api: Discourse,
):
    """
    arrange: given running discourse server
    act: when a topic is created and then updated with an incorrect API key
    assert: then DiscourseError is raised.
    """
    # Create topic
    title = "title 1 padding so it is long enough test_update_topic_auth_error"
    content_1 = "content 1 padding so it is long enough test_update_topic_auth_error"

    url = discourse_api.create_topic(title=title, content=content_1)

    unauth_discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key="invalid key",
        category_id=discourse_category_id,
    )
    content_2 = "content 2 padding so it is long enough test_update_topic_auth_error"

    with pytest.raises(DiscourseError):
        unauth_discourse.update_topic(url=url, content=content_2)


@pytest.mark.asyncio
async def test_delete_topic_auth_error(
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
    discourse_api: Discourse,
):
    """
    arrange: given running discourse server
    act: when a topic is created and then deleted with an incorrect API key
    assert: then DiscourseError is raised.
    """
    # Create topic
    title = "title 1 padding so it is long enough test_delete_topic_auth_error"
    content_1 = "content 1 padding so it is long enough test_delete_topic_auth_error"

    url = discourse_api.create_topic(title=title, content=content_1)

    unauth_discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key="invalid key",
        category_id=discourse_category_id,
    )

    with pytest.raises(DiscourseError):
        unauth_discourse.delete_topic(url=url)


# The test cannot be simplified and all argument are needed
# pylint: disable=too-many-arguments
@pytest.mark.asyncio
async def test_read_write_permission(
    discourse_alternate_user_api_key: str,
    discourse_hostname: str,
    discourse_alternate_user_credentials: types.Credentials,
    discourse_category_id: int,
    discourse_api: Discourse,
):
    """
    arrange: given running discourse server
    act: when a topic is created by one user and the permissions checked for an alternate user
    assert: then the alternate user has the read but not write permission for the topic.
    """
    # Create topic
    title = "title 1 padding so it is long enough test_read_write_permission"
    content_1 = "content 1 padding so it is long enough test_read_write_permission"

    url = discourse_api.create_topic(title=title, content=content_1)

    alternate_user_discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_alternate_user_credentials.username,
        api_key=discourse_alternate_user_api_key,
        category_id=discourse_category_id,
    )

    assert alternate_user_discourse.check_topic_read_permission(
        url=url
    ), "alternate user could not read topic another user created"
    assert (
        alternate_user_discourse.check_topic_write_permission(url=url) is False
    ), "user could write topic another user created"
