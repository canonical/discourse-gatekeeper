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

from src import Clients, constants, exceptions, metadata, repository, run_reconcile
from src.constants import DEFAULT_BRANCH, DISCOURSE_AHEAD_TAG, DOCUMENTATION_TAG
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
    repository_client: repository.Client,
):
    """
    arrange: given running discourse server and mocked GitHub client
    act: when run is called with:
        1. docs with an index and documentation file
        2. docs with a documentation file updated and discourse updated with conflicting content in
            dry run mode
        3. docs with a documentation file updated and discourse updated with conflicting content
        4. docs with a documentation file and discourse updated to resolve conflict
        5. docs with an index and documentation and alternate documentation file
        6. docs with an index and changed documentation and alternate documentation with server
            changes
        7. docs with an index and changed documentation and alternate documentation with server
            changes with upload-charm-docs/discourse-ahead-ok applied
    assert: then:
        1. the documentation page is created
        2. the documentation page is not updated
        3. the documentation page is not updated
        4. the documentation page is updated
        5. the alternate documentation page is created
        6. the documentation page is not updated
        6. the documentation page is updated
    """
    document_name = "name 1"
    caplog.set_level(logging.INFO)

    repository_client.tag_commit(DOCUMENTATION_TAG, repository_client.current_commit)

    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: {document_name}", path=repository_path
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "first commit of metadata", directory=None
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

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "1. docs with an index and documentation file", directory=None
    )

    reconcile_output = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    urls_with_actions = reconcile_output.topics

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

    # 2. docs with a documentation file updated and discourse updated with conflicting content in
    # dry run mode
    caplog.clear()
    doc_file.write_text(
        doc_content_2 := f"# {doc_title}\nline 1a\nline 2\nline 3", encoding="utf-8"
    )
    discourse_api.update_topic(
        url=doc_url, content=(doc_topic_content_2 := f"# {doc_title}\nline 1\nline 2\nline 3a")
    )
    mock_content_file = MagicMock(spec=ContentFile)
    mock_content_file.content = b64encode(doc_content_1.encode(encoding="utf-8"))
    mock_github_repo.get_contents.return_value = mock_content_file

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "2. docs with a documentation file updated and discourse updated with conflicting "
        "content in dry run mode"
    )

    with pytest.raises(exceptions.InputError) as exc_info:
        run_reconcile(
            clients=Clients(discourse=discourse_api, repository=repository_client),
            user_inputs=factories.UserInputsFactory(
                dry_run=True, delete_pages=True, commit_sha=repository_client.current_commit
            ),
        )

    assert_substrings_in_string(
        (
            repr(doc_content_2),
            repr(doc_content_1),
            repr(doc_topic_content_2),
            "problem",
            "preventing",
            "execution",
        ),
        caplog.text,
    )
    assert_substrings_in_string(("actions", "not", "executed"), str(exc_info.value))
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_topic_content_2

    # 3. docs with a documentation file updated and discourse updated with conflicting content
    caplog.clear()

    with pytest.raises(exceptions.InputError) as exc_info:
        run_reconcile(
            clients=Clients(discourse=discourse_api, repository=repository_client),
            user_inputs=factories.UserInputsFactory(
                dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
            ),
        )

    assert_substrings_in_string(
        (
            repr(doc_content_2),
            repr(doc_content_1),
            repr(doc_topic_content_2),
            "problem",
            "preventing",
            "execution",
        ),
        caplog.text,
    )
    assert_substrings_in_string(("actions", "not", "executed"), str(exc_info.value))
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_topic_content_2

    # 4. docs with a documentation file and discourse updated to resolve conflict
    caplog.clear()
    doc_file.write_text(
        doc_content_4 := f"# {doc_title}\nline 1a\nline 2\nline 3a", encoding="utf-8"
    )
    discourse_api.update_topic(url=doc_url, content=doc_content_4)

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "4. docs with a documentation file and discourse updated to resolve conflict"
    )

    reconcile_output = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    urls_with_actions = reconcile_output.topics

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, doc_table_line_1, "Noop", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_4

    # 5. docs with an index and documentation and alternate documentation file
    caplog.clear()
    alt_doc_table_key = "alt-doc"
    alt_doc_title = "alt doc title"
    (docs_dir / f"{alt_doc_table_key}.md").write_text(
        alt_doc_content_5 := f"# {alt_doc_title}\nalt doc content 5", encoding="utf-8"
    )
    doc_file.write_text(doc_content_5 := f"# {doc_title}\ncontent 5", encoding="utf-8")

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "5. docs with an index and documentation and alternate documentation file"
    )
    mock_content_file.content = b64encode(doc_content_4.encode(encoding="utf-8"))

    reconcile_output = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    urls_with_actions = reconcile_output.topics

    assert len(urls_with_actions) == 3
    (alt_doc_url, _, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (alt_doc_url, doc_url, index_url)
    alt_doc_table_line_5 = (
        f"| 1 | {alt_doc_table_key} | [{alt_doc_title}]({urlparse(alt_doc_url).path}) |"
    )
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, alt_doc_table_line_5, "Update", "Create", "'success'")),
        caplog.text,
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    assert alt_doc_table_line_5 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_5
    alt_doc_topic = discourse_api.retrieve_topic(url=alt_doc_url)
    assert alt_doc_topic == alt_doc_content_5

    # 6. docs with an index and changed documentation and alternate documentation with server
    # changes
    caplog.clear()
    doc_file.write_text(doc_content_6 := f"# {doc_title}\ncontent 6", encoding="utf-8")

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "# 6. docs with an index and changed documentation and alternate documentation with "
        "server changes"
    )
    mock_content_file.content = b64encode(doc_content_5.encode(encoding="utf-8"))
    mock_alt_content_file = MagicMock(spec=ContentFile)
    mock_alt_content_file.content = b64encode(alt_doc_content_5.encode(encoding="utf-8"))
    mock_github_repo.get_contents.side_effect = [mock_alt_content_file, mock_content_file]
    discourse_api.update_topic(
        url=alt_doc_url, content=(alt_doc_topic_content_6 := f"# {alt_doc_title}\nalt content 6")
    )

    with pytest.raises(exceptions.InputError) as exc_info:
        run_reconcile(
            clients=Clients(discourse=discourse_api, repository=repository_client),
            user_inputs=factories.UserInputsFactory(
                dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
            ),
        )

    assert_substrings_in_string(
        (
            doc_table_key,
            alt_doc_table_key,
            "problem",
            "preventing",
            "execution",
        ),
        caplog.text,
    )
    assert_substrings_in_string(("actions", "not", "executed"), str(exc_info.value))
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    assert alt_doc_table_line_5 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_5
    alt_doc_topic = discourse_api.retrieve_topic(url=alt_doc_url)
    assert alt_doc_topic == alt_doc_topic_content_6

    # 7. docs with an index and changed documentation and alternate documentation with server
    # changes with upload-charm-docs/discourse-ahead-ok applied
    caplog.clear()
    repository_client.tag_commit(DISCOURSE_AHEAD_TAG, repository_client.current_commit)
    mock_github_repo.get_contents.side_effect = [mock_alt_content_file, mock_content_file]

    reconcile_output = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    urls_with_actions = reconcile_output.topics

    assert len(urls_with_actions) == 3
    (alt_doc_url, _, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (alt_doc_url, doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, alt_doc_table_line_5, "Update", "'success'")),
        caplog.text,
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    assert alt_doc_table_line_5 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_6
    alt_doc_topic = discourse_api.retrieve_topic(url=alt_doc_url)
    assert alt_doc_topic == alt_doc_topic_content_6
