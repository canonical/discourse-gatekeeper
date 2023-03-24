# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for action."""

# Need access to protected functions for testing
# For some reason pylint is detecting duplicate code when there isn't any
# pylint: disable=protected-access,duplicate-code

import logging
from unittest import mock

import pytest

from src import action, discourse, exceptions
from src import types_ as src_types

from ... import factories
from ..helpers import assert_substrings_in_string


@pytest.mark.parametrize(
    "dry_run",
    [
        pytest.param(True, id="dry run mode enabled"),
        pytest.param(False, id="dry run mode disabled"),
    ],
)
def test__update_directory(dry_run: bool, caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a directory, dry run mode and mocked discourse
    act: when action is passed to _update with dry_run
    assert: then no topic is updated, the action is logged and the expected report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    update_action = src_types.UpdateAction(
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=None),
            new=src_types.Navlink(title="title 2", link=None),
        ),
        content_change=None,
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=dry_run
    )

    assert_substrings_in_string((f"action: {update_action}", f"dry run: {dry_run}"), caplog.text)
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.location is None
    assert (
        returned_report.result == src_types.ActionResult.SKIP
        if dry_run
        else src_types.ActionResult.SUCCESS
    )
    assert returned_report.reason == (action.DRY_RUN_REASON if dry_run else None)


def test__update_file_dry_run(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file and mocked discourse
    act: when action is passed to _update with dry_run True
    assert: then no topic is updated, the action is logged and a skip report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    url = "url 1"
    mocked_discourse.absolute_url.return_value = url
    old_content: str
    update_action = src_types.UpdateAction(
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            old=(old_content := "content 1\n"),
            new=(new_content := "content 2\n"),
            base=old_content,
        ),
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=True
    )

    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {True}",
            old_content,
            new_content,
            f"content change:\n- {old_content}?         ^\n+ {new_content}?         ^\n",
        ),
        caplog.text,
    )
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.location == url
    assert returned_report.result == src_types.ActionResult.SKIP
    assert returned_report.reason == action.DRY_RUN_REASON


def test__update_file_navlink_title_change(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file where only the navlink title has changed and mocked
        discourse
    act: when action is passed to _update with dry_run False
    assert: then no topic is updated, the action is logged and the expected table row is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    url = "url 1"
    mocked_discourse.absolute_url.return_value = url
    content: str
    update_action = src_types.UpdateAction(
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            old=(content := "content 1"), new=content, base=None
        ),
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=False
    )

    assert_substrings_in_string(
        (f"action: {update_action}", f"dry run: {False}", content),
        caplog.text,
    )
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.location == url
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


def test__update_file_navlink_content_change_discourse_error(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file where content has changed and mocked discourse that
        raises an error
    act: when action is passed to _update with dry_run False
    assert: then topic is updated, the action is logged and a fail report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    url = "url 1"
    mocked_discourse.absolute_url.return_value = url
    mocked_discourse.update_topic.side_effect = (error := exceptions.DiscourseError("failed"))
    old_content: str
    update_action = src_types.UpdateAction(
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            old=(old_content := "content 1"), new=(new_content := "content 2"), base=old_content
        ),
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=False
    )

    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {False}",
            old_content,
            new_content,
            f"content change:\n- {old_content}\n?         ^\n+ {new_content}\n?         ^\n",
        ),
        caplog.text,
    )
    assert update_action.content_change is not None
    mocked_discourse.update_topic.assert_called_once_with(
        url=link, content=update_action.content_change.new
    )
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.location == url
    assert returned_report.result == src_types.ActionResult.FAIL
    assert returned_report.reason == str(error)


@pytest.mark.parametrize(
    "content_change, expected_log_contents, expected_reason_contents",
    [
        pytest.param(
            factories.ContentChangeFactory(base="x", old="y", new="z"),
            ("content change:\n- x\n+ z\n",),
            ("merge", "conflict"),
            id="merge conflict",
        ),
        pytest.param(
            factories.ContentChangeFactory(base=None, old="y", new="z"),
            (),
            ("no", "base"),
            id="no base",
        ),
    ],
)
def test__update_file_navlink_content_change_conflict(
    content_change: src_types.ContentChange,
    expected_log_contents: tuple[str, ...],
    expected_reason_contents: tuple[str, ...],
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given update action for a file where content has changed and mocked discourse
    act: when action is passed to _update with dry_run False
    assert: then topic is not updated, the action is logged and a fail report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    url = "url 1"
    mocked_discourse.absolute_url.return_value = url
    update_action = src_types.UpdateAction(
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=content_change,
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=False
    )

    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {False}",
            repr(content_change.base),
            repr(content_change.old),
            repr(content_change.new),
            *expected_log_contents,
        ),
        caplog.text,
    )
    assert update_action.content_change is not None
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.location == url
    assert returned_report.result == src_types.ActionResult.FAIL
    assert returned_report.reason is not None
    assert_substrings_in_string(expected_reason_contents, returned_report.reason)


def test__update_file_navlink_content_change(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file where content has changed and mocked discourse
    act: when action is passed to _update with dry_run False
    assert: then topic is updated with merged content, the action is logged and success report is
        returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    url = "url 1"
    mocked_discourse.absolute_url.return_value = url
    old_content: str
    update_action = src_types.UpdateAction(
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            old=(old_content := "line 1a\nline 2\nline 3\n"),
            new=(new_content := "line 1\nline 2\nline 3a\n"),
            base=(base_content := "line 1\nline 2\nline 3\n"),
        ),
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=False
    )

    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {False}",
            repr(base_content),
            repr(old_content),
            repr(new_content),
            "content change:\n  line 1\n  line 2\n- line 3\n+ line 3a\n?       +\n",
        ),
        caplog.text,
    )
    assert update_action.content_change is not None
    mocked_discourse.update_topic.assert_called_once_with(
        url=link, content="line 1a\nline 2\nline 3a\n"
    )
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.location == url
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


def test__update_file_navlink_content_change_error():
    """
    arrange: given update action for a file where content change is None
    act: when action is passed to _update with dry_run False
    assert: ActionError is raised.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    update_action = src_types.UpdateAction(
        level=1,
        path="path 1",
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=None,
    )

    with pytest.raises(exceptions.ActionError):
        action._update(action=update_action, discourse=mocked_discourse, dry_run=False)
