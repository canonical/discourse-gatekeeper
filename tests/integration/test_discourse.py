# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Integration tests for discourse."""

from urllib import parse

import pydiscourse
import pytest

from src.discourse import Discourse, TopicNotFoundError

from . import types


@pytest.mark.asyncio
async def test_create_get_update_unlist_topic(
    discourse_user_api_key: str,
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
    discourse_client: pydiscourse.DiscourseClient,
):
    """
    arrange: given running discourse server
    act: when a topic is created, checked for permissions, retrieved, updated and unlisted
    assert: then all the sequential actions succeed and the topic is unlisted in the end.
    """
    discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key=discourse_user_api_key,
        category_id=discourse_category_id,
    )

    # Create topic
    title = "title 1 padding so it is long enough"
    content_1 = "content 1 padding so it is long enough"

    url = discourse.create_topic(title=title, content=content_1)
    returned_content = discourse.get_topic(url=url)

    assert returned_content == content_1
    # Check that the category is correct
    url_path_components = parse.urlparse(url=url).path.split("/")
    slug = url_path_components[-2]
    topic_id = url_path_components[-1]
    topic = discourse_client.topic(slug=slug, topic_id=topic_id)
    assert topic["category_id"] == discourse_category_id

    # Check permissions
    assert discourse.check_topic_read_permission(url=url)
    assert discourse.check_topic_write_permission(url=url)

    # Update topic
    content_2 = "content 2 padding so it is long enough"
    discourse.update_topic(url=url, content=content_2)
    returned_content = discourse.get_topic(url=url)

    assert returned_content == content_2

    # Unlist topic
    discourse.unlist_topic(url=url)

    with pytest.raises(TopicNotFoundError):
        discourse.get_topic(url=url)
