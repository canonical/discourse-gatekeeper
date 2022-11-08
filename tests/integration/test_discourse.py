# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Integration tests for discourse."""

from urllib import parse

import pydiscourse
import pytest

from src.discourse import Discourse, DiscourseError

from . import types


@pytest.mark.asyncio
async def test_create_retrieve_update_delete_topic(
    discourse_user_api_key: str,
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
    discourse_client: pydiscourse.DiscourseClient,
):
    """
    arrange: given running discourse server
    act: when a topic is created, checked for permissions, retrieved, updated and deleteed
    assert: then all the sequential actions succeed and the topic is deleteed in the end.
    """
    discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key=discourse_user_api_key,
        category_id=discourse_category_id,
    )

    # Create topic
    title = f"title 1 padding so it is long enough test_crud_topic"
    content_1 = "content 1 padding so it is long enough test_crud_topic"

    url = discourse.create_topic(title=title, content=content_1)
    returned_content = discourse.retrieve_topic(url=url)

    assert returned_content == content_1, "post was created with the wrong content"
    # Check that the category is correct
    url_path_components = parse.urlparse(url=url).path.split("/")
    slug = url_path_components[-2]
    topic_id = url_path_components[-1]
    topic = discourse_client.topic(slug=slug, topic_id=topic_id)
    assert (
        topic["category_id"] == discourse_category_id
    ), "post was not created with the correct category id"

    # Check permissions
    assert discourse.check_topic_read_permission(url=url), "user could not read topic they created"
    assert discourse.check_topic_write_permission(
        url=url
    ), "user could not write topic they created"

    # Update topic
    content_2 = "content 2 padding so it is long enough  test_crud_topic"
    discourse.update_topic(url=url, content=content_2)
    returned_content = discourse.retrieve_topic(url=url)

    assert returned_content == content_2, "content was not updated"

    # Delete topic
    discourse.delete_topic(url=url)

    topic = discourse_client.topic(slug=slug, topic_id=topic_id)
    assert "withdrawn" in topic["post_stream"]["posts"][0]["cooked"], "topic not deleted"
    assert topic["post_stream"]["posts"][0]["user_deleted"], "topic not deleted"

    with pytest.raises(DiscourseError):
        discourse.retrieve_topic(url=url)


# Keep the API key parameter to ensure that the API key is created just that the wrone one is being
# used
@pytest.mark.asyncio
async def test_create_topic_auth_error(
    discourse_user_api_key: str,
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
    title = f"title 1 padding so it is long enough test_create_topic_auth_error"
    content_1 = "content 1 padding so it is long enough test_create_topic_auth_error"

    with pytest.raises(DiscourseError):
        discourse.create_topic(title=title, content=content_1)


@pytest.mark.asyncio
async def test_retrieve_topic_auth_error(
    discourse_user_api_key: str,
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
):
    """
    arrange: given running discourse server
    act: when a topic is created and then retrieved with an incorrect API key
    assert: then DiscourseError is raised.
    """
    discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key=discourse_user_api_key,
        category_id=discourse_category_id,
    )

    title = f"title 1 padding so it is long enough test_retrieve_topic_auth_error"
    content_1 = "content 1 padding so it is long enough test_retrieve_topic_auth_error"

    url = discourse.create_topic(title=title, content=content_1)

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
    discourse_user_api_key: str,
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
):
    """
    arrange: given running discourse server
    act: when a topic is created and then updated with an incorrect API key
    assert: then DiscourseError is raised.
    """
    discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key=discourse_user_api_key,
        category_id=discourse_category_id,
    )

    # Create topic
    title = f"title 1 padding so it is long enough test_update_topic_auth_error"
    content_1 = "content 1 padding so it is long enough test_update_topic_auth_error"

    url = discourse.create_topic(title=title, content=content_1)

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
    discourse_user_api_key: str,
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_category_id: int,
):
    """
    arrange: given running discourse server
    act: when a topic is created and then deleteed with an incorrect API key
    assert: then DiscourseError is raised.
    """
    discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key=discourse_user_api_key,
        category_id=discourse_category_id,
    )

    # Create topic
    title = f"title 1 padding so it is long enough test_delete_topic_auth_error"
    content_1 = "content 1 padding so it is long enough test_delete_topic_auth_error"

    url = discourse.create_topic(title=title, content=content_1)

    unauth_discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key="invalid key",
        category_id=discourse_category_id,
    )

    with pytest.raises(DiscourseError):
        unauth_discourse.delete_topic(url=url)


@pytest.mark.asyncio
async def test_read_write_permission(
    discourse_user_api_key: str,
    discourse_alternate_user_api_key: str,
    discourse_hostname: str,
    discourse_user_credentials: types.Credentials,
    discourse_alternate_user_credentials: types.Credentials,
    discourse_category_id: int,
):
    """
    arrange: given running discourse server
    act: when a topic is created by one user and the permissions checked for an alternate user
    assert: then the alternate user has the read but not write permission for the topic.
    """
    discourse = Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key=discourse_user_api_key,
        category_id=discourse_category_id,
    )

    # Create topic
    title = f"title 1 padding so it is long enough test_read_write_permission"
    content_1 = "content 1 padding so it is long enough test_read_write_permission"

    url = discourse.create_topic(title=title, content=content_1)

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


{
    "post_stream": {
        "posts": [
            {
                "id": 16,
                "name": None,
                "username": "user1",
                "avatar_template": "/letter_avatar_proxy/v4/letter/u/5daacb/{size}.png",
                "created_at": "2022-11-08T00:58:51.083Z",
                "cooked": "<p>(topic withdrawn by author, will be automatically deleted in 24 hours unless flagged)</p>",
                "post_number": 1,
                "post_type": 1,
                "updated_at": "2022-11-08T00:58:53.563Z",
                "reply_count": 0,
                "reply_to_post_number": None,
                "quote_count": 0,
                "incoming_link_count": 0,
                "reads": 1,
                "readers_count": 0,
                "score": 0,
                "yours": False,
                "topic_id": 13,
                "topic_slug": "title-1-padding-so-it-is-long-enough-test-crud-topic",
                "display_username": None,
                "primary_group_name": None,
                "primary_group_flair_url": None,
                "primary_group_flair_bg_color": None,
                "primary_group_flair_color": None,
                "version": 3,
                "can_edit": True,
                "can_delete": False,
                "can_recover": False,
                "can_wiki": True,
                "read": False,
                "user_title": None,
                "bookmarked": False,
                "actions_summary": [
                    {"id": 2, "can_act": True},
                    {"id": 3, "can_act": True},
                    {"id": 4, "can_act": True},
                    {"id": 8, "can_act": True},
                    {"id": 6, "can_act": True},
                    {"id": 7, "can_act": True},
                ],
                "moderator": False,
                "admin": False,
                "staff": False,
                "user_id": 2,
                "hidden": False,
                "trust_level": 0,
                "deleted_at": None,
                "user_deleted": True,
                "edit_reason": None,
                "can_view_edit_history": True,
                "wiki": False,
                "notice": {"type": "new_user"},
                "reviewable_id": 0,
                "reviewable_score_count": 0,
                "reviewable_score_pending_count": 0,
            }
        ],
        "stream": [16],
    },
    "timeline_lookup": [[1, 0]],
    "suggested_topics": [
        {
            "id": 7,
            "title": "Welcome to Discourse",
            "fancy_title": "Welcome to Discourse",
            "slug": "welcome-to-discourse",
            "posts_count": 1,
            "reply_count": 0,
            "highest_post_number": 1,
            "image_url": None,
            "created_at": "2022-11-08T00:49:48.365Z",
            "last_posted_at": "2022-11-08T00:49:48.466Z",
            "bumped": True,
            "bumped_at": "2022-11-08T00:49:48.466Z",
            "archetype": "regular",
            "unseen": False,
            "last_read_post_number": 1,
            "unread": 0,
            "new_posts": 0,
            "pinned": True,
            "unpinned": None,
            "excerpt": "The first paragraph of this pinned topic will be visible as a welcome message to all new visitors on your homepage. It’s important! \nEdit this into a brief description of your community: \n\nWho is it for?\nWhat can they fi&hellip;",
            "visible": True,
            "closed": False,
            "archived": False,
            "notification_level": 3,
            "bookmarked": False,
            "liked": False,
            "tags": [],
            "like_count": 0,
            "views": 0,
            "category_id": 1,
            "featured_link": None,
            "posters": [
                {
                    "extras": "latest single",
                    "description": "Original Poster, Most Recent Poster",
                    "user": {
                        "id": -1,
                        "username": "system",
                        "name": "system",
                        "avatar_template": "/images/discourse-logo-sketch-small.png",
                    },
                }
            ],
        }
    ],
    "tags": [],
    "id": 13,
    "title": "Title 1 padding so it is long enough test_crud_topic",
    "fancy_title": "Title 1 padding so it is long enough test_crud_topic",
    "posts_count": 1,
    "created_at": "2022-11-08T00:58:50.852Z",
    "views": 2,
    "reply_count": 0,
    "like_count": 0,
    "last_posted_at": "2022-11-08T00:58:51.083Z",
    "visible": True,
    "closed": True,
    "archived": False,
    "has_summary": False,
    "archetype": "regular",
    "slug": "title-1-padding-so-it-is-long-enough-test-crud-topic",
    "category_id": 5,
    "word_count": 13,
    "deleted_at": None,
    "user_id": 2,
    "featured_link": None,
    "pinned_globally": False,
    "pinned_at": None,
    "pinned_until": None,
    "image_url": None,
    "slow_mode_seconds": 0,
    "draft": None,
    "draft_key": "topic_13",
    "draft_sequence": 0,
    "unpinned": None,
    "pinned": False,
    "current_post_number": 1,
    "highest_post_number": 1,
    "deleted_by": None,
    "has_deleted": False,
    "actions_summary": [
        {"id": 4, "count": 0, "hidden": False, "can_act": True},
        {"id": 8, "count": 0, "hidden": False, "can_act": True},
        {"id": 7, "count": 0, "hidden": False, "can_act": True},
    ],
    "chunk_size": 20,
    "bookmarked": False,
    "topic_timer": None,
    "message_bus_last_id": 3,
    "participant_count": 1,
    "show_read_indicator": False,
    "thumbnails": None,
    "details": {
        "can_edit": True,
        "notification_level": 1,
        "can_move_posts": True,
        "can_delete": True,
        "can_remove_allowed_users": True,
        "can_invite_to": True,
        "can_invite_via_email": True,
        "can_create_post": True,
        "can_reply_as_new_topic": True,
        "can_flag_topic": True,
        "can_convert_topic": True,
        "can_review_topic": True,
        "can_close_topic": True,
        "can_archive_topic": True,
        "can_split_merge_topic": True,
        "can_edit_staff_notes": True,
        "can_toggle_topic_visibility": True,
        "can_pin_unpin_topic": True,
        "can_moderate_category": True,
        "can_remove_self_id": -1,
        "participants": [
            {
                "id": 2,
                "username": "user1",
                "name": None,
                "avatar_template": "/letter_avatar_proxy/v4/letter/u/5daacb/{size}.png",
                "post_count": 1,
                "primary_group_name": None,
                "primary_group_flair_url": None,
                "primary_group_flair_color": None,
                "primary_group_flair_bg_color": None,
                "trust_level": 0,
            }
        ],
        "created_by": {
            "id": 2,
            "username": "user1",
            "name": None,
            "avatar_template": "/letter_avatar_proxy/v4/letter/u/5daacb/{size}.png",
        },
        "last_poster": {
            "id": 2,
            "username": "user1",
            "name": None,
            "avatar_template": "/letter_avatar_proxy/v4/letter/u/5daacb/{size}.png",
        },
    },
}
