# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for running the action."""

# This test is fairly complex as it simulates sequential action runs
# pylint: disable=too-many-arguments,too-many-locals,too-many-statements

import logging
import shutil
from itertools import chain
from pathlib import Path
from urllib.parse import urlparse

import pytest
from git.exc import GitCommandError
from git.repo import Repo
from github.PullRequest import PullRequest

from src import GETTING_STARTED, exceptions, index, metadata, pull_request, reconcile, run
from src.discourse import Discourse

from ..unit.helpers import assert_substrings_in_string, create_metadata_yaml

pytestmark = pytest.mark.init


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_get_repository_name", "patch_create_github")
async def test_run(
    discourse_api: Discourse,
    caplog: pytest.LogCaptureFixture,
    repository: tuple[Repo, Path],
    upstream_repository: tuple[Repo, Path],
    mock_pull_request: PullRequest,
):
    """
    arrange: given running discourse server
    act: when run is called with:
        1. docs empty
        2. docs with an index file in dry run mode
        3. docs with an index file
        4. docs with a documentation file added in dry run mode
        5. docs with a documentation file added
        6. docs with a documentation file updated in dry run mode
        7. docs with a documentation file updated
        8. docs with a nested directory added
        9. docs with a documentation file added in the nested directory
        10. docs with the documentation file in the nested directory removed in dry run mode
        11. docs with the documentation file in the nested directory removed with page deletion
            disabled
        12. with the nested directory removed
        13. with the documentation file removed
        14. with the index file removed
        15. with no docs dir and no custom branchname provided in dry run mode
        16. with no docs dir and no custom branchname provided
        17. with no docs dir and custom branchname provided in dry run mode
        18. with no docs dir and custom branchname provided
        19. with no changes applied after migration in dry run mode
        20. with no changes applied after migration
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
        15. the documentation files are not pushed to default branch
        16. the documentation files are pushed to default branch
        17. the documentation files are not pushed to custom branch
        18. the documentation files are pushed to custom branch
        19. no operations are taken place
        20. no operations are taken place
    """
    (repo, repo_path) = repository
    document_name = "name 1"
    caplog.set_level(logging.INFO)
    create_metadata_yaml(content=f"{metadata.METADATA_NAME_KEY}: {document_name}", path=repo_path)

    # 1. docs empty
    with pytest.raises(exceptions.InputError) as exc_info:
        urls_with_actions = run(
            base_path=repo_path,
            discourse=discourse_api,
            dry_run=False,
            delete_pages=True,
            repo=repo,
            github_access_token="test-access-token",
            branch_name=None,
        )

    assert str(exc_info.value) == GETTING_STARTED

    # 2. docs with an index file in dry run mode
    caplog.clear()
    index_url = discourse_api.create_topic(
        title=f"{document_name.replace('-', ' ').title()} Documentation Overview",
        content=f"{reconcile.NAVIGATION_TABLE_START}".strip(),
    )
    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: name 1\n{metadata.METADATA_DOCS_KEY}: {index_url}",
        path=repo_path,
    )
    (docs_dir := repo_path / index.DOCUMENTATION_FOLDER_NAME).mkdir()
    (index_file := docs_dir / "index.md").write_text(index_content := "index content 1")

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=True,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert tuple(urls_with_actions) == (index_url,)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_topic == f"{reconcile.NAVIGATION_TABLE_START}".strip()
    assert_substrings_in_string((index_url, "Update", "'skip'"), caplog.text)

    # 3. docs with an index file
    caplog.clear()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert tuple(urls_with_actions) == (index_url,)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_topic == f"{index_content}{reconcile.NAVIGATION_TABLE_START}"
    assert_substrings_in_string((index_url, "Update", "'success'"), caplog.text)

    # 4. docs with a documentation file added in dry run mode
    caplog.clear()
    doc_table_key = "doc"
    (doc_file := docs_dir / f"{doc_table_key}.md").write_text(doc_content_1 := "doc content 1")

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=True,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert tuple(urls_with_actions) == (index_url,)
    assert_substrings_in_string(("Create", "'skip'"), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_content_1 not in index_topic

    # 5. docs with a documentation file added
    caplog.clear()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert len(urls_with_actions) == 2
    (doc_url, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    doc_table_line_1 = f"| 1 | {doc_table_key} | [{doc_content_1}]({urlparse(doc_url).path}) |"
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, "Create", "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1

    # 6. docs with a documentation file updated in dry run mode
    caplog.clear()
    doc_file.write_text(doc_content_2 := "doc content 2")

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=True,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(chain(urls, (doc_table_line_1, "Update", "'skip'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_1 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_1

    # 7. docs with a documentation file updated
    caplog.clear()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    doc_table_line_2 = f"| 1 | {doc_table_key} | [{doc_content_2}]({urlparse(doc_url).path}) |"
    assert_substrings_in_string(
        chain(urls, (doc_table_line_1, doc_table_line_2, "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert doc_table_line_2 in index_topic
    doc_topic = discourse_api.retrieve_topic(url=doc_url)
    assert doc_topic == doc_content_2

    # 8. docs with a nested directory added
    caplog.clear()
    nested_dir_table_key = "nested-dir"
    (nested_dir := docs_dir / nested_dir_table_key).mkdir()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    nested_dir_table_line = f"| 1 | {nested_dir_table_key} | [Nested Dir]() |"
    assert_substrings_in_string(
        chain(urls, (nested_dir_table_line, "Create", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_table_line in index_topic

    # 9. docs with a documentation file added in the nested directory
    caplog.clear()
    nested_dir_doc_table_key = "nested-dir-doc"
    (nested_dir_doc_file := nested_dir / "doc.md").write_text(
        nested_dir_doc_content := "nested dir doc content 1"
    )

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert len(urls_with_actions) == 3
    (_, nested_dir_doc_url, _) = urls_with_actions.keys()
    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    nested_dir_doc_table_line = (
        f"| 2 | {nested_dir_doc_table_key} |"
        f" [{nested_dir_doc_content}]({urlparse(nested_dir_doc_url).path}) |"
    )
    assert_substrings_in_string(
        chain(urls, (nested_dir_doc_table_line, "Create", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_doc_table_line in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 10. docs with the documentation file in the nested directory removed in dry run mode
    caplog.clear()
    nested_dir_doc_file.unlink()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=True,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (nested_dir_doc_table_line, "Delete", "Update", "'skip'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_doc_table_line in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 11. docs with the documentation file in the nested directory removed with page deletion
    #     disabled
    caplog.clear()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=False,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, nested_dir_doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (nested_dir_doc_table_line, "Delete", "Update", "'skip'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_doc_table_line not in index_topic
    nested_dir_doc_topic = discourse_api.retrieve_topic(url=nested_dir_doc_url)
    assert nested_dir_doc_topic == nested_dir_doc_content

    # 12. with the nested directory removed
    caplog.clear()
    nested_dir.rmdir()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert (urls := tuple(urls_with_actions)) == (doc_url, index_url)
    assert_substrings_in_string(
        chain(urls, (nested_dir_table_line, "Delete", "Update", "'success'")), caplog.text
    )
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert nested_dir_table_line not in index_topic

    # 13. with the documentation file removed
    caplog.clear()
    doc_file.unlink()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

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

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    assert (urls := tuple(urls_with_actions)) == (index_url,)
    assert_substrings_in_string(chain(urls, ("Update", "'success'")), caplog.text)
    index_topic = discourse_api.retrieve_topic(url=index_url)
    assert index_content not in index_topic

    # 15. with no docs dir and no custom branchname provided in dry run mode
    caplog.clear()
    (upstream_repo, _) = upstream_repository
    doc_table_key_2 = "docs-2"
    nested_dir_table_key_2 = "nested-dir-2"
    (index_file := docs_dir / "index.md").write_text(index_content := "index content 1")
    (doc_file := docs_dir / f"{doc_table_key_2}.md").write_text(doc_content_3 := "doc content 3")
    (nested_dir := docs_dir / nested_dir_table_key_2).mkdir()
    (nested_dir_doc_file := nested_dir / "doc.md").write_text(
        (nested_dir_doc_content_2 := "nested dir doc content 2")
    )
    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=True,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )
    urls = tuple(urls_with_actions)
    shutil.rmtree(docs_dir)

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=True,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    with pytest.raises(GitCommandError) as exc_info:
        upstream_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert_substrings_in_string(
        ("error: pathspec", "did not match any file(s) known to git"), str(exc_info.value)
    )
    assert tuple(urls_with_actions) == (pull_request.PR_LINK_DRY_RUN,)

    # 16. with no docs dir and no custom branchname provided
    caplog.clear()
    doc_table_key_2 = "docs-2"
    nested_dir_table_key_2 = "nested-dir-2"
    (index_file := docs_dir / "index.md").write_text(index_content := "index content 1")
    (doc_file := docs_dir / f"{doc_table_key_2}.md").write_text(doc_content_3 := "doc content 3")
    (nested_dir := docs_dir / nested_dir_table_key_2).mkdir()
    (nested_dir_doc_file := nested_dir / "doc.md").write_text(
        (nested_dir_doc_content_2 := "nested dir doc content 2")
    )
    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )
    urls = tuple(urls_with_actions)
    shutil.rmtree(docs_dir)

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=None,
    )

    upstream_repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    repo.git.checkout(pull_request.DEFAULT_BRANCH_NAME)
    assert tuple(urls_with_actions) == (mock_pull_request.url,)
    assert index_file.read_text(encoding="utf-8") == index_content
    assert doc_file.read_text(encoding="utf-8") == doc_content_3
    assert nested_dir_doc_file.read_text(encoding="utf-8") == nested_dir_doc_content_2

    # 17. with no docs dir and custom branchname provided in dry run mode
    caplog.clear()
    upstream_repo.git.checkout("main")
    repo.git.checkout("main")
    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: name 1\n{metadata.METADATA_DOCS_KEY}: {index_url}",
        path=repo_path,
    )
    custom_branchname = "branchname-1"

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=custom_branchname,
    )

    with pytest.raises(GitCommandError) as exc_info:
        upstream_repo.git.checkout(custom_branchname)
    assert_substrings_in_string(
        ("error: pathspec", "did not match any file(s) known to git"), str(exc_info.value)
    )
    assert tuple(urls_with_actions) == (pull_request.PR_LINK_DRY_RUN,)

    # 18. with no docs dir and custom branchname provided
    caplog.clear()
    upstream_repo.git.checkout("main")
    repo.git.checkout("main")
    create_metadata_yaml(
        content=f"{metadata.METADATA_NAME_KEY}: name 1\n{metadata.METADATA_DOCS_KEY}: {index_url}",
        path=repo_path,
    )
    custom_branchname = "branchname-1"

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=custom_branchname,
    )

    upstream_repo.git.checkout(custom_branchname)
    repo.git.checkout(custom_branchname)
    assert tuple(urls_with_actions) == (mock_pull_request.url,)
    assert index_file.read_text(encoding="utf-8") == index_content
    assert doc_file.read_text(encoding="utf-8") == doc_content_3
    assert (nested_dir / "doc.md").read_text(encoding="utf-8") == nested_dir_doc_content_2

    # 19. with no changes applied after migration in dry run mode
    caplog.clear()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=custom_branchname,
    )

    with pytest.raises(GitCommandError) as exc_info:
        upstream_repo.git.checkout(custom_branchname)
    assert_substrings_in_string(
        ("error: pathspec", "did not match any file(s) known to git"), str(exc_info.value)
    )
    assert_substrings_in_string(chain(urls, ("Noop", "Noop", "Noop", "'success'")), caplog.text)

    # 20. with no changes applied after migration
    caplog.clear()

    urls_with_actions = run(
        base_path=repo_path,
        discourse=discourse_api,
        dry_run=False,
        delete_pages=True,
        repo=repo,
        github_access_token="test-access-token",
        branch_name=custom_branchname,
    )

    assert_substrings_in_string(chain(urls, ("Noop", "Noop", "Noop", "'success'")), caplog.text)
