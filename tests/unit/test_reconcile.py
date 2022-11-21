# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for reconcile module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path

from src import reconcile, types_


def test__create_page_action_file(tmp_path: Path):
    """
    arrange: given path info with a file
    act: when _create_page_action is called with the path info
    assert: then a create page action with the file content is returned.
    """
    (path := tmp_path / "file1.md").touch()
    content = "content 1"
    path.write_text(content, encoding="utf-8")
    path_info = types_.PathInfo(
        local_path=path, level=1, table_path="table path 1", navlink_title="title 1"
    )

    returned_action = reconcile._create_page_action(path_info=path_info)

    assert returned_action.action == types_.PageAction.CREATE
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    assert returned_action.navlink_title == path_info.navlink_title
    assert returned_action.content == content


def test__create_page_action_directory(tmp_path: Path):
    """
    arrange: given path info with a directory
    act: when _create_page_action is called with the path info
    assert: then a create page action for the directory.
    """
    (path := tmp_path / "dir1").mkdir()
    path_info = types_.PathInfo(
        local_path=path, level=1, table_path="table path 1", navlink_title="title 1"
    )

    returned_action = reconcile._create_page_action(path_info=path_info)

    assert returned_action.action == types_.PageAction.CREATE
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    assert returned_action.navlink_title == path_info.navlink_title
    assert returned_action.content is None
