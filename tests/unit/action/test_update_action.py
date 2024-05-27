# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for action."""

# Need access to protected functions for testing
# For some reason pylint is detecting duplicate code when there isn't any
# pylint: disable=protected-access,duplicate-code

import logging
from unittest import mock

import pytest

from gatekeeper import action, discourse, exceptions
from gatekeeper import types_ as src_types

from ... import factories
from ..helpers import assert_substrings_in_string


def _test__update_directory_parameters():
    """Generate parameters for the test__update_directory test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            action_1 := factories.UpdateExternalRefActionFactory(),
            True,
            action_1.navlink_change.new.link,
            id="external ref dry run mode enabled",
        ),
        pytest.param(
            action_1 := factories.UpdateExternalRefActionFactory(),
            False,
            action_1.navlink_change.new.link,
            id="external ref dry run mode disabled",
        ),
        pytest.param(
            factories.UpdateGroupActionFactory(), True, None, id="group dry run mode enabled"
        ),
        pytest.param(
            factories.UpdateGroupActionFactory(), False, None, id="group dry run mode disabled"
        ),
    ]


@pytest.mark.parametrize(
    "update_action, dry_run, expected_location", _test__update_directory_parameters()
)
def test__update_directory(
    update_action: src_types.UpdateAction,
    dry_run: bool,
    expected_location: str | None,
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given update action for a directory or external ref, dry run mode and mocked discourse
    act: when action is passed to _update with dry_run
    assert: then no topic is updated, the action is logged and the expected report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=dry_run
    )

    assert_substrings_in_string((f"action: {update_action}", f"dry run: {dry_run}"), caplog.text)
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == update_action.level
    assert returned_report.table_row.path == update_action.path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.location == expected_location
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
    server_content: str
    update_action = factories.UpdatePageActionFactory(
        level=(level := 1),
        path=(path := ("path 1",)),
        navlink_change=factories.NavlinkChangeFactory(
            old=factories.NavlinkFactory(title="title 1", link=(link := "link 1")),
            new=factories.NavlinkFactory(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            server=(server_content := "content 1\n"),
            local=(local_content := "content 2\n"),
            base=server_content,
        ),
    )
    dry_run = True

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=dry_run
    )

    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {dry_run}",
            server_content,
            local_content,
            f"content change:\n- {server_content}?         ^\n+ {local_content}?         ^\n",
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
        discourse and the content missing from the default branch
    act: when action is passed to _update with dry_run False
    assert: then no topic is updated, the action is logged and the expected table row is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    url = "url 1"
    mocked_discourse.absolute_url.return_value = url
    content: str
    update_action = factories.UpdatePageActionFactory(
        level=(level := 1),
        path=(path := ("path 1",)),
        navlink_change=factories.NavlinkChangeFactory(
            old=factories.NavlinkFactory(title="title 1", link=(link := "link 1")),
            new=factories.NavlinkFactory(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            server=(content := "content 1"), local=content, base=None
        ),
    )
    dry_run = False

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=dry_run
    )

    assert_substrings_in_string(
        (f"action: {update_action}", f"dry run: {dry_run}", content),
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


def test__update_file_navlink_hidden_change(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file where only the navlink hidden has changed and mocked
        discourse and the content missing from the default branch
    act: when action is passed to _update with dry_run False
    assert: then no topic is updated, the action is logged and the expected table row is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    url = "url 1"
    mocked_discourse.absolute_url.return_value = url
    content: str
    update_action = factories.UpdatePageActionFactory(
        level=(level := 1),
        path=(path := ("path 1",)),
        navlink_change=factories.NavlinkChangeFactory(
            old=factories.NavlinkFactory(
                title=(title := "title 1"), link=(link := "link 1"), hidden=False
            ),
            new=factories.NavlinkFactory(title=title, link=link, hidden=True),
        ),
        content_change=src_types.ContentChange(
            server=(content := "content 1"), local=content, base=None
        ),
    )
    dry_run = False

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=dry_run
    )

    assert_substrings_in_string(
        (f"action: {update_action}", f"dry run: {dry_run}", content),
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
    server_content = "content 1"
    mocked_discourse.retrieve_topic.return_value = server_content
    mocked_discourse.update_topic.side_effect = (error := exceptions.DiscourseError("failed"))
    update_action = factories.UpdatePageActionFactory(
        level=(level := 1),
        path=(path := ("path 1",)),
        navlink_change=factories.NavlinkChangeFactory(
            old=factories.NavlinkFactory(title="title 1", link=(link := "link 1")),
            new=factories.NavlinkFactory(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            server=server_content,
            local=(local_content := "content 2"),
            base=server_content,
        ),
    )
    dry_run = False

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=dry_run
    )

    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {dry_run}",
            server_content,
            local_content,
            f"content change:\n- {server_content}\n?         ^\n+ {local_content}\n?         ^\n",
        ),
        caplog.text,
    )
    assert update_action.content_change is not None
    mocked_discourse.update_topic.assert_called_once_with(
        url=link, content=update_action.content_change.local
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
            factories.ContentChangeFactory(base="x", server="y", local="z"),
            ("content change:\n- x\n+ z\n",),
            ("merge", "conflict"),
            id="merge conflict",
        ),
        pytest.param(
            factories.ContentChangeFactory(base=None, server="y", local="z"),
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
    mocked_discourse.retrieve_topic.return_value = content_change.server
    update_action = factories.UpdatePageActionFactory(
        level=(level := 1),
        path=(path := ("path 1",)),
        navlink_change=factories.NavlinkChangeFactory(
            old=factories.NavlinkFactory(title="title 1", link=(link := "link 1")),
            new=factories.NavlinkFactory(title="title 2", link=link),
        ),
        content_change=content_change,
    )
    dry_run = False

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=dry_run
    )

    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {dry_run}",
            repr(content_change.base),
            repr(content_change.server),
            repr(content_change.local),
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


def test__update_file_navlink_content_change_post_check_conflict(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file where content has changed and mocked discourse where
        the server content has changed since the conflict check was done
    act: when action is passed to _update with dry_run False
    assert: then an ActionError is raised.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    url = "url 1"
    mocked_discourse.absolute_url.return_value = url
    server_content_1 = "line 1a\nline 2\nline 3\n"
    server_content_2 = "line 1b\nline 2\nline 3\n"
    mocked_discourse.retrieve_topic.return_value = server_content_1
    update_action = factories.UpdatePageActionFactory(
        navlink_change=factories.NavlinkChangeFactory(
            old=factories.NavlinkFactory(title="title 1", link=(link := "link 1")),
            new=factories.NavlinkFactory(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            server=server_content_2,
            local=(local_content := "line 1\nline 2\nline 3a\n"),
            base=(base_content := "line 1\nline 2\nline 3\n"),
        ),
    )
    dry_run = False

    with pytest.raises(exceptions.ActionError) as exc:
        action._update(action=update_action, discourse=mocked_discourse, dry_run=dry_run)

    assert_substrings_in_string(
        (link, "has changed", "conflict check"),
        str(exc),
    )
    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {dry_run}",
            repr(base_content),
            repr(server_content_2),
            repr(local_content),
            "content change:\n  line 1\n  line 2\n- line 3\n+ line 3a\n?       +\n",
        ),
        caplog.text,
    )
    assert update_action.content_change is not None
    mocked_discourse.update_topic.assert_not_called()


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
    server_content = "line 1a\nline 2\nline 3\n"
    mocked_discourse.retrieve_topic.return_value = server_content
    update_action = factories.UpdatePageActionFactory(
        level=(level := 1),
        path=(path := ("path 1",)),
        navlink_change=factories.NavlinkChangeFactory(
            old=factories.NavlinkFactory(title="title 1", link=(link := "link 1")),
            new=factories.NavlinkFactory(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(
            server=server_content,
            local=(local_content := "line 1\nline 2\nline 3a\n"),
            base=(base_content := "line 1\nline 2\nline 3\n"),
        ),
    )
    dry_run = False

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, dry_run=dry_run
    )

    assert_substrings_in_string(
        (
            f"action: {update_action}",
            f"dry run: {dry_run}",
            repr(base_content),
            repr(server_content),
            repr(local_content),
            "content change:\n  line 1\n  line 2\n- line 3\n+ line 3a\n?       +\n",
        ),
        caplog.text,
    )
    assert update_action.content_change is not None
    mocked_discourse.retrieve_topic.assert_called_once_with(url=link)
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
