# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for running the action."""

# This test is fairly complex as it simulates sequential action runs
# pylint: disable=too-many-arguments,too-many-locals

import logging
from pathlib import Path
from urllib.parse import urlparse
from itertools import chain

import pytest

from src import index, reconcile, run, exceptions
from src.discourse import Discourse

from ..unit.helpers import create_metadata_yaml, assert_substrings_in_string


@pytest.mark.asyncio
async def test_run(discourse_api: Discourse, tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """
    arrange: given running discourse server
    act: when run is called with:
        1. docs empty
        2. docs with an index file in draft mode
        3. docs with an index file
        4. docs with a documentation file added in draft mode
        5. docs with a documentation file added
        6. docs with a documentation file updated in draft mode
        7. docs with a documentation file updated
        8. docs with a nested directory added
        9. docs with a documentation file added in the nested directory
        10. docs with the documentation file in the nested directory removed in draft mode
        11. docs with the documentation file in the nested directory removed with page deletion
            disabled
        12. with the nested directory removed
        13. with the documentation file removed
        14. with the index file removed
    assert: then:
        1. an index page is created with an empty navigation table
        2. an index page is not updated
        3. an index page is updated
        4. the documentation page is not created
        5. the documentation page is created
        6. the documentation page is not updated
        7. the documentation page is updated
        8. the nested directory is added to the navigation table
        9. the documentation file in the nested directory is created
        10. the documentation file in the nested directory is not removed
        11. the documentation file in the nested directory is not removed
        12. the nested directory is removed from the navigation table
        13. the documentation page is deleted
        14. an index page is not updated
    """
    caplog.set_level(logging.INFO)
    create_metadata_yaml(content=f"{index.METADATA_NAME_KEY}: name 1", path=tmp_path)

    # 1. docs empty
    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert len(urls_with_actions) == 1
    index_url = next(iter(urls_with_actions.keys()))
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_topic == f"{reconcile.NAVIGATION_TABLE_START}"
    assert index_url in caplog.text

    # 2. docs with an index file in draft mode
    caplog.clear()
    create_metadata_yaml(
        content=f"{index.METADATA_NAME_KEY}: name 1\n{index.METADATA_DOCS_KEY}: {index_url}",
        path=tmp_path,
    )
    (docs_dir := tmp_path / "docs").mkdir()
    (index_file := docs_dir / "index.md").write_text(index_content := "index content 1")

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=True, delete_pages=True
    )

    assert tuple(urls_with_actions) == (index_url,)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_topic == f"{reconcile.NAVIGATION_TABLE_START}"
    assert_substrings_in_string((index_url, "'update'", "'skip'"), caplog.text)

    # 3. docs with an index file
    caplog.clear()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert tuple(urls_with_actions) == (index_url,)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_topic == f"{index_content}{reconcile.NAVIGATION_TABLE_START}"
    assert_substrings_in_string((index_url, "'update'", "'success'"), caplog.text)

    # 4. docs with a documentation file added in draft mode
    caplog.clear()
    doc_table_key = "doc"
    (doc_file := docs_dir / f"{doc_table_key}.md").write_text(doc_content_1 := "doc content 1")

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=True, delete_pages=True
    )

    assert tuple(urls_with_actions) == (index_url,)
    assert_substrings_in_string(("'create'", "'skip'"), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_content_1 not in index_topic

    # 5. docs with a documentation file added
    caplog.clear()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert len(urls_with_actions) == 2
    (doc_url, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'create'", "'update'", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    doc_table_line_1 = f"| 1 | {doc_table_key} | [{doc_content_1}]({urlparse(doc_url).path}) |"
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1

    # 6. docs with a documentation file updated in draft mode
    caplog.clear()
    doc_file.write_text(doc_content_2 := "doc content 2")

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=True, delete_pages=True
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'update'", "'skip'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1

    # 7. docs with a documentation file updated
    caplog.clear()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'update'", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    doc_table_line_2 = f"| 1 | {doc_table_key} | [{doc_content_2}]({urlparse(doc_url).path}) |"
    assert doc_table_line_2 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_2

    # 8. docs with a nested directory added
    caplog.clear()
    nested_dir_table_key = "nested-dir"
    (nested_dir := docs_dir / nested_dir_table_key).mkdir()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'create'", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    nested_dir_table_line = f"| 1 | {nested_dir_table_key} | [Nested Dir]() |"
    assert nested_dir_table_line in index_topic

    # 9. docs with a documentation file added in the nested directory
    caplog.clear()
    nested_dir_doc_table_key = "nested-dir-doc"
    (nested_dir_doc_file := nested_dir / "doc.md").write_text(
        nested_dir_doc_content := "nested dir doc content 1"
    )

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert len(urls_with_actions) == 3
    (_, nested_dir_doc_url, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'create'", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    nested_dir_doc_table_line = (
        f"| 2 | {nested_dir_doc_table_key} |"
        f" [{nested_dir_doc_content}]({urlparse(nested_dir_doc_url).path}) |"
    )
    assert nested_dir_doc_table_line in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 10. docs with the documentation file in the nested directory removed in draft mode
    caplog.clear()
    nested_dir_doc_file.unlink()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=True, delete_pages=True
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'delete'", "'update'", "'skip'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_doc_table_line in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 11. docs with the documentation file in the nested directory removed with page deletion
    #     disabled
    caplog.clear()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=False
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'delete'", "'update'", "'skip'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_doc_table_line not in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 12. with the nested directory removed
    caplog.clear()
    nested_dir.rmdir()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'delete'", "'update'", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_table_line not in index_topic

    # 13. with the documentation file removed
    caplog.clear()
    doc_file.unlink()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("'delete'", "'update'", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_2 not in index_topic
    with pytest.raises(exceptions.DiscourseError):
        discourse_api.retrieve_topic(url=doc_url)

    # 14. with the index file removed
    caplog.clear()
    index_file.unlink()

    urls_with_actions = run(
        base_path=tmp_path, discourse=discourse_api, draft_mode=False, delete_pages=True
    )

    assert (urls := tuple(urls_with_actions)) == (index_url,)
    assert_substrings_in_string(chain(urls, ("'update'", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content not in index_topic
