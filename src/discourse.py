# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Interface for Discourse interactions."""

import typing
from urllib import parse

import pydiscourse
import pydiscourse.exceptions


class _DiscourseTopicInfo(typing.NamedTuple):
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
        self._category_id = category_id
        self._base_path = base_path

    @staticmethod
    def _retrieve_topic_info_from_url(url: str) -> _DiscourseTopicInfo:
        """
        Retrieve the topic information from the url to the topic.

        Args:
            url: The URL to the topic.

        Returns:
            The topic information.

        """
        path_components = parse.urlparse(url=url).path.split("/")
        return _DiscourseTopicInfo(slug=path_components[-2], id_=path_components[-1])

    def _retrieve_topic_first_post(self, url: str) -> dict:
        """
        Retrieve the first post from a topic based on the URL to the topic.

        Raises DiscourseError is pydiscourse raises an error or if the topic has been deleted.

        Args:
            usl: The URL ot the topic.

        Returns:
            The first post from the topic.

        """
        topic_info = self._retrieve_topic_info_from_url(url=url)
        try:
            topic = self.client.topic(slug=topic_info.slug, topic_id=topic_info.id_)
        except pydiscourse.exceptions.DiscourseError as discourse_error:
            raise DiscourseError from discourse_error

        first_post = next(
            filter(lambda post: post["post_number"] == 1, topic["post_stream"]["posts"])
        )
        # Check for deleted topic
        if first_post["user_deleted"]:
            raise DiscourseError(f"topic has been deleted, {url=}")
        return first_post

    def check_topic_write_permission(self, url: str) -> bool:
        """
        Check whether the credentials have write permission on a topic.

        Raises AuthenticationError if authentication fails and TopicNotFoundError if the topic is not
        found.

        Args:
            url: The URL to the topic. Assume it includes the slug and id of the topic as the last
                2 elements of the url.

        Returns:
            Whether the credentials have write permissions to the topic.

        """
        first_post = self._retrieve_topic_first_post(url=url)
        return first_post["can_edit"]

    def check_topic_read_permission(self, url: str) -> bool:
        """
        Check whether the credentials have read permission on a topic.

        Use whether retrieve topic succeeds as inidication whether the read permission is available.

        Raises AuthenticationError if authentication fails and TopicNotFoundError if the topic is not
        found.

        Args:
            url: The URL to the topic. Assume it includes the slug and id of the topic as the last
                2 elements of the url.

        Returns:
            Whether the credentials have read permissions to the topic.

        """
        self._retrieve_topic_first_post(url=url)
        return True

    def retrieve_topic(self, url: str) -> str:
        """
        Retrieve the topic content.

        Raises AuthenticationError if authentication fails, AuthorizationError if the server refuses to
        return the requested topic and TopicNotFoundError if the topic is not found.

        Args:
            url: The URL to the topic. Assume it includes the slug and id of the topic as the last
                2 elements of the url.

        Returns:
            The content of the first post in the topic.

        """
        first_post = self._retrieve_topic_first_post(url=url)
        return first_post["cooked"].removeprefix("<p>").removesuffix("</p>")

    def create_topic(self, title: str, content: str) -> str:
        """
        Create a new topic.

        Raises DiscourseError if anything goes wrong.

        Args:
            title: The title of the topic.
            content: The content for the first post in the topic.

        Returns:
            The URL to the topic.

        """
        try:
            post = self.client.create_post(
                title=title, category_id=self._category_id, tags=self.tags, content=content
            )
        except pydiscourse.exceptions.DiscourseError as discourse_error:
            raise DiscourseError from discourse_error

        return f"{self._base_path}/t/{post['topic_slug']}/{post['topic_id']}"

    def delete_topic(self, url: str) -> None:
        """
        Delete a topic.

        Raises AuthenticationError if authentication fails, AuthorizationError if the server refuses
        to unlist the topic, TopicNotFoundError if the topic is not found or CommunicationError if
        anything else has gone wrong.

        Args:
            url: The URL to the topic.

        """
        topic_info = self._retrieve_topic_info_from_url(url=url)
        try:
            self.client.delete_topic(topic_id=topic_info.id_)
        except pydiscourse.exceptions.DiscourseError as discourse_error:
            raise DiscourseError from discourse_error

    def update_topic(self, url: str, content: str) -> None:
        """
        Update the first post of a topic.

        Raises AuthenticationError if authentication fails, AuthorizationError if the server refuses
        to update the first post in the topic and TopicNotFoundError if the topic is not found.

        Args:
            url: The URL to the topic.
            content: The content for the first post in the topic.

        """
        first_post = self._retrieve_topic_first_post(url=url)
        try:
            self.client.update_post(
                post_id=first_post["id"],
                content=content,
                edit_reason="Charm documentation updated",
            )
        except pydiscourse.exceptions.DiscourseError as discourse_error:
            raise DiscourseError from discourse_error
