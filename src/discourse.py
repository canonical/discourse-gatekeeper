# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Interface for Discourse interactions."""

from urllib import parse

import pydiscourse
import pytest


class DiscourseError(Exception):
    """Parent exception for all Discourse errors."""


class AuthenticationError(DiscourseError):
    """Authentication with the server failed."""


class AuthorizationError(DiscourseError):
    """The server refused to take a requested action."""


class TopicNotFoundError(DiscourseError):
    """The topic was not found on the server."""

    def __init__(self, url: str) -> None:
        """Constructor."""
        super().__init__()
        self.url = url


class Discourse:
    """Interact with a discourse server."""

    tags = ("docs",)

    def __init__(self, base_path: str, api_username: str, api_key: str, category_id: int) -> None:
        """
        Constructor.

        Args:
            base_path: The HTTP protocol and hostname for discourse (e.g., https://discourse).
            api_username: The username to use for API requests.
            api_key: The API key for requests.
            category_id: The category identify to put the topics into.

        """
        self.client = pydiscourse.DiscourseClient(
            host=base_path, api_username=api_username, api_key=api_key
        )
        self.category = category_id
        self.base_path = base_path

    def check_topic_write_permission(self, url: str) -> bool:
        """
        Check whether the credentials have write permission on a topic.

        Raises AuthenticationError if authentication fails and TopicNotFoundError if the topic is not
        found.

        Args:
            url: The URL to the topic.

        Returns:
            Whether the credentials have write permissions to the topic.

        """
        pytest.set_trace()

    def check_topic_read_permission(self, url: str) -> bool:
        """
        Check whether the credentials have read permission on a topic.

        Raises AuthenticationError if authentication fails and TopicNotFoundError if the topic is not
        found.

        Args:
            url: The URL to the topic.

        Returns:
            Whether the credentials have read permissions to the topic.

        """
        pytest.set_trace()

    def get_topic(self, url: str) -> str:
        """
        Retrieve the topic content.

        Raises AuthenticationError if authentication fails, AuthorizationError if the server refuses to
        return the requested topic and TopicNotFoundError if the topic is not found.

        Args:
            url: The URL to the topic.

        Returns:
            The content of the first post in the topic.

        """
        topic_id = parse.urlparse(url=url).path.split("/")[-1]
        topic_posts = self.client.topic_posts(topic_id=topic_id)
        post = next(
            filter(lambda post: post["post_number"] == 1, topic_posts["post_stream"]["posts"])
        )
        return post["cooked"].removeprefix("<p>").removesuffix("</p>")

    def create_topic(self, title: str, content: str) -> str:
        """
        Create a new topic.

        Raises AuthenticationError if authentication fails and AuthorizationError if the server refuses
        to create the new topic.

        Args:
            title: The title of the topic.
            content: The content for the first post in the topic.

        Returns:
            The URL to the topic.

        """
        post = self.client.create_post(
            title=title, category_id=self.category, tags=self.tags, content=content
        )
        return f"{self.base_path}/t/{post['topic_slug']}/{post['topic_id']}"

    def unlist_topic(self, url: str) -> None:
        """
        Unlist a topic.

        Raises AuthenticationError if authentication fails, AuthorizationError if the server refuses
        to unlist the topic and TopicNotFoundError if the topic is not found.

        Args:
            url: The URL to the topic.

        """
        pytest.set_trace()

    def update_topic(self, url: str, content: str) -> None:
        """
        Update the first post of a topic.

        Raises AuthenticationError if authentication fails, AuthorizationError if the server refuses
        to update the first post in the topic and TopicNotFoundError if the topic is not found.

        Args:
            url: The URL to the topic.
            content: The content for the first post in the topic.

        """
        pytest.set_trace()
