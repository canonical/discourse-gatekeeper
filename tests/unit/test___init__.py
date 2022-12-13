# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for execution."""

from pathlib import Path
from unittest import mock

from src import discourse, exceptions, metadata, reconcile, run, types_

from .helpers import create_metadata_yaml


def test_run_empty_local_server(tmp_path: Path):
    """
    arrange: given metadata with name but not docs and empty docs folder and mocked discourse
    act: when run is called
    assert: then an index page is created with empty navigation table.
    """
    create_metadata_yaml(content=f"{metadata.METADATA_NAME_KEY}: name 1", path=tmp_path)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.return_value = (url := "url 1")

    returned_page_interactions = run(
        base_path=tmp_path, discourse=mocked_discourse, dry_run=False, delete_pages=True
    )

    mocked_discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{reconcile.NAVIGATION_TABLE_START.strip()}",
    )
    assert returned_page_interactions == {url: types_.ActionResult.SUCCESS}


def test_run_local_empty_server(tmp_path: Path):
    """
    arrange: given metadata with name but not docs and docs folder with a file and mocked discourse
    act: when run is called
    assert: then a documentation page is created and an index page is created with a navigation
        page with a reference to the documentation page.
    """
    name = "name 1"
    create_metadata_yaml(content=f"{metadata.METADATA_NAME_KEY}: {name}", path=tmp_path)
    (docs_folder := tmp_path / "docs").mkdir()
    (docs_folder / "index.md").write_text(index_content := "index content")
    (docs_folder / "page.md").write_text(page_content := "page content")
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.side_effect = [
        (page_url := "url 1"),
        (index_url := "url 2"),
    ]

    returned_page_interactions = run(
        base_path=tmp_path, discourse=mocked_discourse, dry_run=False, delete_pages=True
    )

    assert mocked_discourse.create_topic.call_count == 2
    mocked_discourse.create_topic.assert_any_call(
        title=f"{name} docs: {page_content}", content=page_content
    )
    mocked_discourse.create_topic.assert_any_call(
        title="Name 1 Documentation Overview",
        content=(
            f"{index_content}{reconcile.NAVIGATION_TABLE_START}\n"
            f"| 1 | page | [{page_content}]({page_url}) |"
        ),
    )
    assert returned_page_interactions == {
        page_url: types_.ActionResult.SUCCESS,
        index_url: types_.ActionResult.SUCCESS,
    }


def test_run_local_empty_server_dry_run(tmp_path: Path):
    """
    arrange: given metadata with name but not docs and docs folder with a file and mocked discourse
    act: when run is called with dry run mode enabled
    assert: no pages are created.
    """
    create_metadata_yaml(content=f"{metadata.METADATA_NAME_KEY}: name 1", path=tmp_path)
    (docs_folder := tmp_path / "docs").mkdir()
    (docs_folder / "index.md").write_text("index content")
    (docs_folder / "page.md").write_text("page content")
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)

    returned_page_interactions = run(
        base_path=tmp_path, discourse=mocked_discourse, dry_run=True, delete_pages=True
    )

    mocked_discourse.create_topic.assert_not_called()
    assert not returned_page_interactions


def test_run_local_empty_server_error(tmp_path: Path):
    """
    arrange: given metadata with name but not docs and empty docs directory and mocked discourse
        that raises an exception
    act: when run is called
    assert: no pages are created.
    """
    create_metadata_yaml(content=f"{metadata.METADATA_NAME_KEY}: name 1", path=tmp_path)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.side_effect = exceptions.DiscourseError

    returned_page_interactions = run(
        base_path=tmp_path, discourse=mocked_discourse, dry_run=False, delete_pages=True
    )

    mocked_discourse.create_topic.assert_called_once_with(
        title="Name 1 Documentation Overview",
        content=f"{reconcile.NAVIGATION_TABLE_START.strip()}",
    )
    assert not returned_page_interactions
