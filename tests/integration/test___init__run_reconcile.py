# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for running the reconcile portion of the action."""

# This test is fairly complex as it simulates sequential action runs
# pylint: disable=too-many-arguments,too-many-locals,too-many-statements

import logging
import shutil
from base64 import b64encode
from itertools import chain
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest
from github.ContentFile import ContentFile

from src import Clients, constants, exceptions, metadata, run_reconcile
from src.constants import DEFAULT_BRANCH, DOCUMENTATION_TAG
from src.discourse import Discourse
from src.repository import Client, Repo

from .. import factories
from ..unit.helpers import assert_substrings_in_string, create_metadata_yaml

pytestmark = pytest.mark.reconcile


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_create_repository_client")
async def test_run(
    discourse_api: Discourse,
    caplog: pytest.LogCaptureFixture,
    repository_path: Path,
    mock_github_repo: MagicMock,
):
    """
    arrange: given running discourse server
    act: when run is called with:
        1. docs with an index file in dry run mode
        2. docs with an index file
        3. docs with a documentation file added in dry run mode
        4. docs with a documentation file added
        5. docs with a documentation file updated in dry run mode
        6. docs with a documentation file updated
        7. docs with a nested directory added
        8. docs with a documentation file added in the nested directory
        9. docs with index file with a local contents index
        10. docs with the documentation file in the nested directory removed in dry run mode
        11. docs with the documentation file in the nested directory removed with page deletion
            disabled
        12. with the nested directory removed
        13. with the documentation file removed
        14. with the index file removed
    assert: then:
        1. an index page is not updated
        2. an index page is updated
        3. the documentation page is not created
        4. the documentation page is created
        5. the documentation page is not updated
        6. the documentation page is updated
        7. the nested directory is added to the navigation table
        8. the documentation file in the nested directory is created
        9. the navigation table is updated based on the contents index
        10. the documentation file in the nested directory is not removed
        11. the documentation file in the nested directory is not removed
        12. the nested directory is removed from the navigation table
        13. the documentation page is deleted
        14. an index page is not updated
    """
    document_name = "name 1"
    caplog.set_level(logging.INFO)

    repository_client = Client(Repo(repository_path), mock_github_repo)

    repository_client.tag_commit(DOCUMENTATION_TAG, repository_client.current_commit)

    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: {document_name}", path=repository_path
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "first commit of metadata", directory=None
    )

    # 1. docs with an index file in dry run mode
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
    (index_file := docs_dir / "index.md").write_text(
        index_content := "index content 1", encoding="utf-8"
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "1. docs with an index file in dry run mode", directory=None
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=True, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    assert output_reconcile.index_url == index_url
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_topic == f"{constants.NAVIGATION_TABLE_START}".strip()
    assert_substrings_in_string((index_url, "Update", "'skip'"), caplog.text)
    mock_github_repo.create_git_ref.assert_not_called()

    # 2. docs with an index file
    caplog.clear()
    user_inputs_2 = factories.UserInputsFactory(
        dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=user_inputs_2,
    )

    assert output_reconcile is not None
    assert output_reconcile.index_url == index_url
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_topic == f"{index_content}{constants.NAVIGATION_TABLE_START}"
    assert_substrings_in_string((index_url, "Update", "'success'"), caplog.text)

    # 3. docs with a documentation file added in dry run mode
    caplog.clear()
    doc_table_key = "doc"
    (doc_file := docs_dir / f"{doc_table_key}.md").write_text(
        doc_content_1 := "doc content 1", encoding="utf-8"
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "3. docs with a documentation file added in dry run mode"
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=True, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    assert output_reconcile.index_url == index_url
    assert_substrings_in_string(("Create", "'skip'"), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_content_1 not in index_topic

    # 4. docs with a documentation file added
    caplog.clear()

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    assert len(output_reconcile.topics) == 2
    (doc_url, _) = output_reconcile.topics.keys()
    assert (urls := tuple(output_reconcile.topics)) == (doc_url, index_url)
    doc_table_line_1 = f"| 1 | {doc_table_key} | [{doc_content_1}]({urlparse(doc_url).path}) |"
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, "Create", "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1

    # 5. docs with a documentation file updated in dry run mode
    caplog.clear()
    doc_file.write_text(doc_content_2 := "doc content 2", encoding="utf-8")
    mock_content_file = MagicMock(spec=ContentFile)
    mock_content_file.content = b64encode(doc_content_1.encode(encoding="utf-8"))
    mock_github_repo.get_contents.return_value = mock_content_file

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "5. docs with a documentation file updated in dry run mode"
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=True, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    assert (urls := tuple(output_reconcile.topics)) == (doc_url, index_url)
    assert_substrings_in_string(chain(urls, (doc_table_line_1, "Update", "'skip'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1
    mock_github_repo.get_contents.assert_called_once_with(
        str(doc_file.relative_to(repository_path)),
        mock_github_repo.get_git_tag.return_value.object.sha,
    )

    # 6. docs with a documentation file updated
    caplog.clear()

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    assert (urls := tuple(output_reconcile.topics)) == (doc_url, index_url)
    doc_table_line_2 = f"| 1 | {doc_table_key} | [{doc_content_2}]({urlparse(doc_url).path}) |"
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, doc_table_line_2, "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_2 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_2

    # 7. docs with a nested directory added
    caplog.clear()
    nested_dir_table_key = "nested-dir"
    (nested_dir := docs_dir / nested_dir_table_key).mkdir()
    (nested_dir / ".gitkeep").touch()

    repository_client.switch(DEFAULT_BRANCH).update_branch("7. docs with a nested directory added")

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    assert (urls := tuple(output_reconcile.topics)) == (doc_url, index_url)
    nested_dir_table_line_1 = f"| 1 | {nested_dir_table_key} | [Nested Dir]() |"
    assert_substrings_in_string(
        chain(urls, (nested_dir_table_line_1, "Create", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_table_line_1 in index_topic

    # 8. docs with a documentation file added in the nested directory
    caplog.clear()
    nested_dir_doc_table_key = "nested-dir-doc"
    (nested_dir_doc_file := nested_dir / "doc.md").write_text(
        nested_dir_doc_content := "nested dir doc content 1", encoding="utf-8"
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "8. docs with a documentation file added in the nested directory"
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert urls_with_actions is not None
    assert len(urls_with_actions) == 3
    (_, nested_dir_doc_url, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    nested_dir_doc_table_line_1 = (
        f"| 2 | {nested_dir_doc_table_key} |"
        f" [{nested_dir_doc_content}]({urlparse(nested_dir_doc_url).path}) |"
    )
    assert_substrings_in_string(
        chain(urls, (nested_dir_doc_table_line_1, "Create", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_doc_table_line_1 in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 9. docs with index file with a local contents index
    caplog.clear()
    nested_dir_doc_file_rel_path = nested_dir_doc_file.relative_to(docs_dir)
    index_file.write_text(
        f"""{index_content}
# contents
- [{(doc_title := "doc title")}]({doc_file.relative_to(docs_dir)})
- [{(nested_dir_title := "nested dir title")}]({nested_dir.relative_to(docs_dir)})
  - [{(nested_dir_doc_title := "nested dir doc title")}]({nested_dir_doc_file_rel_path})
""",
        encoding="utf-8",
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "9. docs with index file with a local contents index"
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None

    urls_with_actions = output_reconcile.topics
    assert len(urls_with_actions) == 3
    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    doc_table_line_3 = f"| 1 | {doc_table_key} | [{doc_title}]({urlparse(doc_url).path}) |"
    nested_dir_table_line_2 = f"| 1 | {nested_dir_table_key} | [{nested_dir_title}]() |"
    nested_dir_doc_table_line_2 = (
        f"| 2 | {nested_dir_doc_table_key} |"
        f" [{nested_dir_doc_title}]({urlparse(nested_dir_doc_url).path}) |"
    )
    assert_substrings_in_string(
        chain(
            urls,
            (
                doc_table_line_3,
                nested_dir_table_line_2,
                nested_dir_doc_table_line_2,
                "Update",
                "'success'",
            ),
        ),
        caplog.text,
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_table_line_2 in index_topic
    assert nested_dir_doc_table_line_2 in index_topic
    assert doc_table_line_3 in index_topic

    # 10. docs with the documentation file in the nested directory removed in dry run mode
    caplog.clear()
    index_file.write_text(index_content, encoding="utf-8")
    nested_dir_doc_file.unlink()

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "10. docs with the documentation file in the nested directory removed in dry run mode"
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=True, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (nested_dir_doc_table_line_2, "Delete", "Update", "'skip'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_doc_table_line_2 in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 11. docs with the documentation file in the nested directory removed with page deletion
    # disabled
    caplog.clear()

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=False, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (nested_dir_doc_table_line_2, "Delete", "Update", "'skip'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_doc_table_line_2 not in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 12. with the nested directory removed
    caplog.clear()
    shutil.rmtree(nested_dir)

    repository_client.switch(DEFAULT_BRANCH).update_branch("12. with the nested directory removed")

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (nested_dir_table_line_1, "Delete", "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_table_line_1 not in index_topic

    # 13. with the documentation file removed
    caplog.clear()
    doc_file.unlink()

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "13. with the documentation file removed"
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (doc_table_line_2, "Delete", "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_2 not in index_topic
    with pytest.raises(exceptions.DiscourseError):
        discourse_api.retrieve_topic(url=doc_url)

    # 14. with the index file removed
    caplog.clear()
    index_file.unlink()

    repository_client.switch(DEFAULT_BRANCH).update_branch("14. with the index file removed")

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert not output_reconcile


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_create_repository_client")
async def test_run_hidden(
    discourse_api: Discourse,
    caplog: pytest.LogCaptureFixture,
    repository_path: Path,
    mock_github_repo: MagicMock,
):
    """
    arrange: given running discourse server
    act: when run is called with:
        1. docs with an index file with a documentation file
        2. docs with an index file with a documentation file changed to hidden
        3. docs with an index file with a hidden documentation file updated
        4. docs with an index file with a hidden documentation file and a new hidden alternate
            documentation file
        5. docs with an index file with a hidden documentation and hidden alternate documentation
            file removed
    assert: then:
        1. the index and documentation page are created
        2. documentation page changed to hidden
        3. documentation page updated
        4. alternate documentation page created
        5. documentation and alternate documentation page removed
    """
    document_name = "hidden name 1"
    caplog.set_level(logging.INFO)

    repository_client = Client(Repo(repository_path), mock_github_repo)

    repository_client.tag_commit(DOCUMENTATION_TAG, repository_client.current_commit)

    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: {document_name}", path=repository_path
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "first commit of metadata", directory=None
    )

    # 1. docs with an index file with a documentation file
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
    doc_table_key = "doc"
    (doc_file := docs_dir / f"{doc_table_key}.md").write_text(
        doc_content_1 := "doc content 1", encoding="utf-8"
    )
    (index_file := docs_dir / "index.md").write_text(
        f"""{(index_content := "index content 1")}
# contents
- [{(doc_title := "hidden doc title")}]({doc_file.relative_to(docs_dir)})
""",
        encoding="utf-8",
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "1. docs with an index file with a documentation file", directory=None
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert len(urls_with_actions) == 2
    (doc_url, index_url) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    doc_table_line_1 = f"| 1 | {doc_table_key} | [{doc_title}]({urlparse(doc_url).path}) |"
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, "Create", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content in index_topic
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1

    # 2. docs with an index file with a documentation file changed to hidden
    caplog.clear()
    index_file.write_text(
        f"""{(index_content := "index content 1")}
# contents
<!-- - [{doc_title}]({doc_file.relative_to(docs_dir)}) -->
""",
        encoding="utf-8",
    )
    mock_content_file = MagicMock(spec=ContentFile)
    mock_content_file.content = b64encode(doc_content_1.encode(encoding="utf-8"))
    mock_github_repo.get_contents.return_value = mock_content_file

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "2. docs with an index file with a documentation file changed to hidden", directory=None
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, "Update", "'success'")), caplog.text
    )
    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    doc_table_line_2 = f"| | {doc_table_key} | [{doc_title}]({urlparse(doc_url).path}) |"
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content in index_topic
    assert doc_table_line_2 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1

    # 3. docs with an index file with a hidden documentation file updated
    caplog.clear()
    doc_file.write_text(doc_content_3 := "doc content 3", encoding="utf-8")

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "3. docs with an index file with a hidden documentation file updated", directory=None
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert_substrings_in_string(
        chain(urls, (doc_table_line_2, "Update", "'success'")), caplog.text
    )
    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content in index_topic
    assert doc_table_line_2 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_3

    # 4. docs with an index file with a hidden documentation file and a new hidden alternate
    # documentation file
    caplog.clear()
    mock_content_file = MagicMock(spec=ContentFile)
    mock_content_file.content = b64encode(doc_content_3.encode(encoding="utf-8"))
    mock_github_repo.get_contents.return_value = mock_content_file
    alt_doc_table_key = "alt-doc"
    (alt_doc_file := docs_dir / f"{alt_doc_table_key}.md").write_text(
        alt_doc_content_4 := "alt doc content 4", encoding="utf-8"
    )
    index_file.write_text(
        f"""{(index_content)}
# contents
<!-- - [{doc_title}]({doc_file.relative_to(docs_dir)}) -->
<!-- - [{(alt_doc_title := "hidden alt doc title")}]({alt_doc_file.relative_to(docs_dir)}) -->
""",
        encoding="utf-8",
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "4. docs with an index file with a hidden documentation file and a new hidden alternate",
        directory=None,
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert len(urls_with_actions) == 3
    (_, alt_doc_url, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (doc_url, alt_doc_url, index_url)
    alt_doc_table_line_4 = (
        f"| | {alt_doc_table_key} | [{alt_doc_title}]({urlparse(alt_doc_url).path}) |"
    )
    assert_substrings_in_string(
        chain(urls, (doc_table_line_2, alt_doc_table_line_4, "Create", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content in index_topic
    assert doc_table_line_2 in index_topic
    assert alt_doc_table_line_4 in index_topic
    alt_doc_topic = discourse_api.retrieve_topic(url=alt_doc_url)
    assert alt_doc_topic == alt_doc_content_4

    # 5. docs with an index file with a hidden documentation and hidden alternate documentation
    # file removed
    caplog.clear()
    doc_file.unlink()
    alt_doc_file.unlink()
    index_file.write_text(index_content, encoding="utf-8")
    mock_alt_content_file = MagicMock(spec=ContentFile)
    mock_alt_content_file.content = b64encode(alt_doc_content_4.encode(encoding="utf-8"))
    mock_github_repo.get_contents.side_effect = [mock_content_file, mock_alt_content_file]

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "5. docs with an index file with a hidden documentation and hidden alternate",
        directory=None,
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert (urls := tuple(urls_with_actions)) == (alt_doc_url, doc_url, index_url)
    assert_substrings_in_string(chain(urls, ("Delete", "Update", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content in index_topic
    assert doc_table_line_2 not in index_topic
    assert alt_doc_table_line_4 not in index_topic
    with pytest.raises(exceptions.DiscourseError):
        discourse_api.retrieve_topic(url=doc_url)
    with pytest.raises(exceptions.DiscourseError):
        discourse_api.retrieve_topic(url=alt_doc_url)


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_create_repository_client")
async def test_run_external(
    discourse_api: Discourse,
    caplog: pytest.LogCaptureFixture,
    repository_path: Path,
    mock_github_repo: MagicMock,
):
    """
    arrange: given running discourse server
    act: when run is called with:
        1. docs with an index file with an external item
        2. docs with an index file with with an external item not changed
        3. docs with an index file with with an external item changed
        4. docs with an index file with with an external item removed
    assert: then:
        1. the index is created with external item
        2. no change
        3. index updated with updated external item
        4. index updated with removed external item
    """
    document_name = "external name 1"
    caplog.set_level(logging.INFO)

    repository_client = Client(Repo(repository_path), mock_github_repo)

    repository_client.tag_commit(DOCUMENTATION_TAG, repository_client.current_commit)

    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: {document_name}", path=repository_path
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "first commit of metadata", directory=None
    )

    # 1. docs with an index file with an external item
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
    (index_file := docs_dir / "index.md").write_text(
        f"""{(index_content := "index content 1")}
# contents
- [{(item_title_1 := "external item title 1")}]({(item_url_1 := "https://canonical.com")})
""",
        encoding="utf-8",
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "1. docs with an index file with an external item", directory=None
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert len(urls_with_actions) == 2
    (external_url, index_url) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (external_url, index_url)
    item_table_line_1 = f"| 1 | https-canonical-com | [{item_title_1}]({item_url_1}) |"
    assert_substrings_in_string(
        chain(urls, (item_table_line_1, "Create", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content in index_topic
    assert item_table_line_1 in index_topic
    assert external_url == item_url_1

    # 2. docs with an index file with with an external item not changed
    caplog.clear()

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is None

    # 3. docs with an index file with with an external item changed
    caplog.clear()
    index_file.write_text(
        f"""{(index_content := "index content 1")}
# contents
- [{(item_title_3 := "external item title 3")}]({(external_url)})
""",
        encoding="utf-8",
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "3. docs with an index file with with an external item changed", directory=None
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert output_reconcile is not None
    urls_with_actions = output_reconcile.topics

    assert len(urls_with_actions) == 2
    (external_url, index_url) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (external_url, index_url)
    item_table_line_3 = f"| 1 | https-canonical-com | [{item_title_3}]({external_url}) |"
    assert_substrings_in_string(
        chain(urls, (item_table_line_3, "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content in index_topic
    assert item_table_line_3 in index_topic
    assert external_url == external_url

    # 4. docs with an index file with with an external item removed
    caplog.clear()
    index_file.write_text(
        f"""{(index_content := "index content 1")}
# contents
""",
        encoding="utf-8",
    )

    repository_client.switch(DEFAULT_BRANCH).update_branch(
        "4. docs with an index file with with an external item removed",
        directory=None,
    )

    output_reconcile = run_reconcile(
        clients=Clients(discourse=discourse_api, repository=repository_client),
        user_inputs=factories.UserInputsFactory(
            dry_run=False, delete_pages=True, commit_sha=repository_client.current_commit
        ),
    )

    assert_substrings_in_string(chain(urls, (item_table_line_3, "'success'")), caplog.text)
    assert (urls := tuple(urls_with_actions)) == (external_url, index_url)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content in index_topic
    assert item_table_line_3 not in index_topic
