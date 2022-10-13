# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Interface for Discourse interactions."""

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

    def __init__(self, host: str, api_username: str, api_key: str, category: int) -> None:
        """Constructor."""
        self.client = pydiscourse.DiscourseClient(
            host=f"http://{host}", api_username=api_username, api_key=api_key
        )
        self.category = category

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
        pytest.set_trace()

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
        pytest.set_trace()
        self.client.create_post(
            title=title, category_id=self.category, tags=self.tags, content=content
        )

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
