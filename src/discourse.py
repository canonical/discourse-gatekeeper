# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Interface for Discourse interactions."""

import typing
from urllib import parse

import pydiscourse
import pytest


class DiscourseTopicInfo(typing.NamedTuple):
    """
    Information about a discourse topic.

    Attrs:
        slug: The slug for the topic.
        id: The identifier for the topic.

    """

    slug: str
    id_: str


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

    @staticmethod
    def _get_topic_info_from_url(url: str) -> DiscourseTopicInfo:
        """
        Get the topic information from the url to the topic.

        Args:
            url: The URL to the topic.

        Returns:
            The topic information.

        """
        path_components = parse.urlparse(url=url).path.split("/")
        return DiscourseTopicInfo(slug=path_components[-2], id_=path_components[-1])

    def _get_topic_first_post(self, url: str) -> dict:
        """
        Get the first post from a topic based on the URL to the topic.

        Args:
            usl: The URL ot the topic.

        Returns:
            The first post from the topic.

        """
        topic_info = self._get_topic_info_from_url(url=url)
        topic = self.client.topic(slug=topic_info.slug, topic_id=topic_info.id_)
        return next(filter(lambda post: post["post_number"] == 1, topic["post_stream"]["posts"]))

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
        first_post = self._get_topic_first_post(url=url)
        return first_post["can_edit"]

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
        first_post = self._get_topic_first_post(url=url)
        return first_post["read"]

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
        first_post = self._get_topic_first_post(url=url)
        return first_post["cooked"].removeprefix("<p>").removesuffix("</p>")

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
        first_post = self._get_topic_first_post(url=url)
        self.client.update_post(
            post_id=first_post["id"], content=content, edit_reason="Charm documentation updated"
        )
