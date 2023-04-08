# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for running the action where there is a merge conflict."""

# This test is fairly complex as it simulates sequential action runs
# pylint: disable=too-many-arguments,too-many-locals,too-many-statements
# The tests for reconcile are similar, although it is better to have some minor duplication than
# make the tests less clear
# pylint: disable = duplicate-code

import logging
from base64 import b64encode
from itertools import chain
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest
from github.ContentFile import ContentFile

from src import constants, exceptions, metadata, run
from src.discourse import Discourse

from .. import factories
from ..unit.helpers import assert_substrings_in_string, create_metadata_yaml

pytestmark = pytest.mark.conflict


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_create_repository_client")
async def test_run_conflict(
    discourse_api: Discourse,
    caplog: pytest.LogCaptureFixture,
    repository_path: Path,
    mock_github_repo: MagicMock,
):
    """
    arrange: given running discourse server and mocked GitHub client
    act: when run is called with:
        1. docs with an index and documentation file
        2. docs with a documentation file updated and discourse updated with non-conflicting
            content
        3. docs with a documentation file updated and discourse updated with conflicting content in
            dry run mode
        4. docs with a documentation file updated and discourse updated with conflicting content
        5. docs with a documentation file and discourse updated to resolve conflict
    assert: then:
        1. the documentation page is created
        2. the documentation page is updated
        3. the documentation page is not updated
        4. the documentation page is not updated
        5. the documentation page is updated
    """
    document_name = "name 1"
    caplog.set_level(logging.INFO)
    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: {document_name}", path=repository_path
    )

    # 1. docs with an index and documentation file
    caplog.clear()
    index_url = discourse_api.create_topic(
        title=f"{document_name.replace('-', ' ').title()} Documentation Overview",
        content=f"{constants.NAVIGATION_TABLE_START}".strip(),
    )
    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: name 1\n{metadata.METADATA_DOCS_KEY}: {index_url}",
        path=repository_path,
    )
    (docs_dir := repository_path / constants.DOCUMENTATION_FOLDER_NAME).mkdir()
    (docs_dir / "index.md").write_text("index content 1", encoding="utf-8")
    doc_table_key = "doc"
    doc_title = "doc title"
    (doc_file := docs_dir / f"{doc_table_key}.md").write_text(
        doc_content_1 := f"# {doc_title}\nline 1\nline 2\nline 3", encoding="utf-8"
    )

    urls_with_actions = run(
        base_path=repository_path,
        discourse=discourse_api,
        user_inputs=factories.UserInputsFactory(dry_run=False, delete_pages=True),
    )

    assert len(urls_with_actions) == 2
    (doc_url, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    doc_table_line_1 = f"| 1 | {doc_table_key} | [{doc_title}]({urlparse(doc_url).path}) |"
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, "Create", "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1

    # 2. docs with a documentation file updated and discourse updated with non-conflicting content
    caplog.clear()
    doc_file.write_text(
        doc_content_2 := f"# {doc_title}\nline 1a\nline 2\nline 3", encoding="utf-8"
    )
    discourse_api.update_topic(url=doc_url, content=f"# {doc_title}\nline 1\nline 2\nline 3a")
    mock_content_file = MagicMock(spec=ContentFile)
    mock_content_file.content = b64encode(doc_content_1.encode(encoding="utf-8"))
    mock_github_repo.get_contents.return_value = mock_content_file

    urls_with_actions = run(
        base_path=repository_path,
        discourse=discourse_api,
        user_inputs=factories.UserInputsFactory(dry_run=False, delete_pages=True),
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, doc_table_line_1, "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == f"# {doc_title}\nline 1a\nline 2\nline 3a"
    mock_github_repo.get_contents.assert_called_once_with(
        str(doc_file.relative_to(repository_path))
    )

    # 3. docs with a documentation file updated and discourse updated with conflicting content in
    # dry run mode
    caplog.clear()
    doc_file.write_text(f"# {doc_title}\nline 1a\nline 2a\nline 3", encoding="utf-8")
    discourse_api.update_topic(
        url=doc_url, content=(doc_topic_content_3 := f"# {doc_title}\nline 1a\nline 2b\nline 3a")
    )
    mock_content_file.content = b64encode(doc_content_2.encode(encoding="utf-8"))

    with pytest.raises(exceptions.InputError) as exc_info:
        run(
            base_path=repository_path,
            discourse=discourse_api,
            user_inputs=factories.UserInputsFactory(dry_run=True, delete_pages=True),
        )

    assert_substrings_in_string(
        (
            "could not automatically merge, conflicts:\\n",
            "# doc title\\n",
            "line 1a\\n",
            "<<<<<<< HEAD\\n",
            "line 2a\\n",
            "line 3\\n",
            "=======\\n",
            "line 2b\\n",
            "line 3a\\n",
            ">>>>>>> theirs\\n",
        ),
        caplog.text,
    )
    assert_substrings_in_string(("actions", "not", "executed"), str(exc_info.value))
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_topic_content_3

    # 4. docs with a documentation file updated and discourse updated with conflicting content
    caplog.clear()

    with pytest.raises(exceptions.InputError) as exc_info:
        run(
            base_path=repository_path,
            discourse=discourse_api,
            user_inputs=factories.UserInputsFactory(dry_run=False, delete_pages=True),
        )

    assert_substrings_in_string(
        (
            "could not automatically merge, conflicts:\\n",
            "# doc title\\n",
            "line 1a\\n",
            "<<<<<<< HEAD\\n",
            "line 2a\\n",
            "line 3\\n",
            "=======\\n",
            "line 2b\\n",
            "line 3a\\n",
            ">>>>>>> theirs\\n",
        ),
        caplog.text,
    )
    assert_substrings_in_string(("actions", "not", "executed"), str(exc_info.value))
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_topic_content_3

    # 5. docs with a documentation file and discourse updated to resolve conflict
    caplog.clear()
    doc_file.write_text(
        doc_content_4 := f"# {doc_title}\nline 1a\nline 2c\nline 3a", encoding="utf-8"
    )
    discourse_api.update_topic(url=doc_url, content=doc_content_4)

    urls_with_actions = run(
        base_path=repository_path,
        discourse=discourse_api,
        user_inputs=factories.UserInputsFactory(dry_run=False, delete_pages=True),
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, doc_table_line_1, "Noop", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_4
