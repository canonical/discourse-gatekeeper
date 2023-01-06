# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for transforming index table rows into local files."""

import itertools
import logging
import typing
from pathlib import Path

from . import exceptions, types_
from .discourse import Discourse
from .docs_directory import calculate_table_path

EMPTY_DIR_REASON = "<created due to empty directory>"
GITKEEP_FILENAME = ".gitkeep"


def _extract_name_from_paths(current_path: Path, table_path: types_.TablePath) -> str:
    """Extract name given a current working directory and table path.

    If there is a matching prefix in table path's prefix generated from the current directory,
    the prefix is removed and the remaining segment is returned as the extracted name.

    Args:
        current_path: current path of the file relative to the directory.
        table_path: table path of the file from the index file, of format path-to-file-filename.

    Returns:
        The filename derived by removing the directory path from given table path of the file.
    """
    return table_path.removeprefix(f"{calculate_table_path(current_path)}-")


def _assert_valid_row(group_level: int, row: types_.TableRow, is_first_row: bool) -> None:
    """Chekcs validity of the row with respect to group level.

    Args:
        group_level: Group level in which the previous row was evaluated in.
        row: Current row to be evaluated.
        is_first_row: True if current row is the first row in table.

    Raises:
        InputError on invalid row level or invalid row level sequence.
    """
    if is_first_row:
        if row.level != 1:
            raise exceptions.InputError(
                "Invalid starting row level. A table row must start with level value 1. "
                "Please fix the upstream first and re-run."
                f"Row: {row=!r}"
            )
    if row.level < 1:
        raise exceptions.InputError(
            f"Invalid row level: {row.level=!r}."
            "Zero or negative level value is invalid."
            f"Row: {row=!r}"
        )
    if row.level > group_level + 1:
        raise exceptions.InputError(
            "Invalid row level value sequence. Level sequence jumps of more than 1 is invalid."
            f"Did you mean level {group_level+1}?"
            f"Row: {row=!r}"
        )


def _get_next_group_info(
    row: types_.TableRow, group_path: Path, group_level: int
) -> tuple[Path, int]:
    """Get next directory path representation of a group with it's level.

    Algorithm:
        1. Set target group level as one above current row level.
        2. While current group level is not equal to target group level
            2.1. If current group level is lower than target,
                should not be possible since it should have been caught during validation step.
                target_group_level being bigger than group_level means traversing more than 1 level
                at a given step.
            2.2. If current group level is higher than target, decrement level and adjust path by
                moving to parent path.
        3. If row is a group row, increment level and adjust path by appending extracted row name.

    Args:
        row: Table row in which to move the path to.
        group_path: Path representation of current group.
        group_level: Current group level.

    Returns:
        A tuple consisting of next directory path representation of group and next group level.
    """
    target_group_level = row.level - 1

    while group_level != target_group_level:
        group_level -= 1
        group_path = group_path.parent

    if row.is_group:
        group_level += 1
        group_path = group_path / _extract_name_from_paths(
            current_path=group_path, table_path=row.path
        )

    return (group_path, group_level)


def _should_yield_gitkeep(row: types_.TableRow, next_level: int, level: int) -> bool:
    """Determine whether to yield a gitkeep file depending on level traversal.

    It is important to note that the previous row must have been an empty a group row.

    Args:
        row: Current table row to evaluate whether a gitkeep should be yielded first.
        next_level: Incoming group level of current table row.
        level: Current level being evaluated.

    Returns:
        True if gitkeep file should be yielded first before processing the row further.
    """
    return (row.is_group and next_level <= level) or (not row.is_group and next_level < level)


def _create_document_meta(row: types_.TableRow, path: Path) -> types_.DocumentMeta:
    """Create document meta file for migration from table row.

    Args:
        row: Row containing link to document and path information.
        path: Relative path to where the document should reside.
    """
    # this is to help mypy understand that link is not None.
    # this case cannot be possible since this is called for group rows only.
    if not row.navlink.link:  # pragma: no cover
        raise exceptions.MigrationError(
            "Internal error, no implementation for creating document meta with missing link in row."
        )
    name = _extract_name_from_paths(current_path=path, table_path=row.path)
    return types_.DocumentMeta(path=path / f"{name}.md", link=row.navlink.link, table_row=row)


def _create_gitkeep_meta(row: types_.TableRow, path: Path) -> types_.GitkeepMeta:
    """Create a representation of an empty grouping through a .gitkeep file metadata.

    Args:
        row: An empty group row.
        path: Relative path to where the document should reside.
    """
    return types_.GitkeepMeta(path=path / GITKEEP_FILENAME, table_row=row)


def _extract_docs_from_table_rows(
    table_rows: typing.Iterable[types_.TableRow],
) -> typing.Generator[types_.MigrationFileMeta, None, None]:
    """Extract necessary migration documents to build docs directory from server.

    Algorithm:
        1. For each row:
            1.1. Check if the row is valid with respect to current group level.
            1.2. Calculate next group level and next group path from row.
            1.3. If previous row was a group and
                the current row is a document and we're traversing up the path OR
                the current row is a folder and we're in the in the same path or above,
                yield a gitkeep meta.
            1.4. Update current group level and current group path.
            1.5. If current row is a document, yield document meta.
        2. If last row was a group, yield gitkeep meta.

    Args:
        table_rows: Table rows from the index file in the order of group hierarchy.

    Raises:
        InputError if invalid row level or invalid sequence of row level is found.

    Yields:
        Migration documents with navlink to content. .gitkeep file if empty group.
    """
    group_level = 0
    current_path = Path()
    previous_row: types_.TableRow | None = None

    for row in table_rows:
        _assert_valid_row(group_level=group_level, row=row, is_first_row=previous_row is None)
        (next_group_path, next_group_level) = _get_next_group_info(
            group_path=current_path, row=row, group_level=group_level
        )
        # if previously processed row was a group and it had nothing in it
        # it should yield a .gitkeep file to denote empty group.
        if (
            previous_row
            and previous_row.is_group
            and _should_yield_gitkeep(row=row, next_level=next_group_level, level=group_level)
        ):
            yield _create_gitkeep_meta(row=previous_row, path=current_path)

        group_level = next_group_level
        current_path = next_group_path
        if not row.is_group:
            yield _create_document_meta(row=row, path=current_path)

        previous_row = row

    # last group without documents yields gitkeep meta.
    if previous_row is not None and previous_row.is_group:
        yield _create_gitkeep_meta(row=previous_row, path=current_path)


def _index_file_from_content(content: str) -> types_.IndexDocumentMeta:
    """Get index file document metadata.

    Args:
        content: Index file content.

    Returns:
        Index file document metadata.
    """
    return types_.IndexDocumentMeta(path=Path("index.md"), content=content)


def _build_path(docs_path: Path, document_meta: types_.MigrationFileMeta) -> Path:
    """Construct path leading to document to be created.

    Args:
        docs_path: Path to documentation directory.
        document_meta: Information about document to be migrated.

    Returns:
        Full path to document to be migrated.
    """
    path = docs_path / document_meta.path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _migrate_gitkeep(gitkeep_meta: types_.GitkeepMeta, docs_path: Path) -> types_.ActionReport:
    """Write gitkeep file to docs directory.

    Args:
        gitkeep_meta: Information about gitkeep file to be migrated.
        docs_path: Documentation folder path.

    Returns:
        Migration report for gitkeep file creation.
    """
    logging.info("migrate meta: %s", gitkeep_meta)

    full_path = _build_path(docs_path=docs_path, document_meta=gitkeep_meta)
    return types_.ActionReport(
        table_row=gitkeep_meta.table_row,
        result=types_.ActionResult.SUCCESS,
        location=full_path,
        reason=EMPTY_DIR_REASON,
    )


def _migrate_document(
    document_meta: types_.DocumentMeta, discourse: Discourse, docs_path: Path
) -> types_.ActionReport:
    """Write document file with content to docs directory.

    Args:
        document_meta: Information about document file to be migrated.
        discourse: Client to the documentation server.
        docs_path: The path to the docs directory to migrate all the documentation.

    Returns:
        Migration report for document file creation.
    """
    logging.info("migrate meta: %s", document_meta)

    try:
        content = discourse.retrieve_topic(url=document_meta.link)
    except exceptions.DiscourseError as exc:
        return types_.ActionReport(
            table_row=document_meta.table_row,
            result=types_.ActionResult.FAIL,
            location=None,
            reason=str(exc),
        )
    full_path = _build_path(docs_path=docs_path, document_meta=document_meta)
    full_path.write_text(content, encoding="utf-8")
    return types_.ActionReport(
        table_row=document_meta.table_row,
        result=types_.ActionResult.SUCCESS,
        location=full_path,
        reason=None,
    )


def _migrate_index(index_meta: types_.IndexDocumentMeta, docs_path: Path) -> types_.ActionReport:
    """Write index document to docs repository.

    Args:
        index_meta: Information about index file to be migrated.
        docs_path: The path to the docs directory to migrate all the documentation.

    Returns:
        Migration report for index file creation.
    """
    logging.info("migrate meta: %s", index_meta)

    full_path = _build_path(docs_path=docs_path, document_meta=index_meta)
    full_path.write_text(index_meta.content, encoding="utf-8")
    return types_.ActionReport(
        table_row=None,
        result=types_.ActionResult.SUCCESS,
        location=full_path,
        reason=None,
    )


def _run_one(
    file_meta: types_.MigrationFileMeta, discourse: Discourse, docs_path: Path
) -> types_.ActionReport:
    """Write document content relative to docs directory.

    Args:
        file_meta: Information about migration file corresponding to a row in index table.
        discourse: Client to the documentation server.
        docs_path: The path to the docs directory to migrate all the documentation.

    Returns:
        Migration report containing migration result.
    """
    match type(file_meta):
        case types_.GitkeepMeta:
            # To help mypy (same for the rest of the asserts), it is ok if the assert does not run
            assert isinstance(file_meta, types_.GitkeepMeta)  # nosec
            report = _migrate_gitkeep(gitkeep_meta=file_meta, docs_path=docs_path)
        case types_.DocumentMeta:
            assert isinstance(file_meta, types_.DocumentMeta)  # nosec
            report = _migrate_document(
                document_meta=file_meta, discourse=discourse, docs_path=docs_path
            )
        case types_.IndexDocumentMeta:
            assert isinstance(file_meta, types_.IndexDocumentMeta)  # nosec
            report = _migrate_index(index_meta=file_meta, docs_path=docs_path)
        # Edge case that should not be possible.
        case _:  # pragma: no cover
            raise exceptions.MigrationError(
                f"Internal error, no implementation for migration file, {file_meta=!r}"
            )

    logging.info("report: %s", report)
    return report


def _get_docs_metadata(
    table_rows: typing.Iterable[types_.TableRow], index_content: str
) -> typing.Iterable[types_.MigrationFileMeta]:
    """Get metadata for documents to be migrated.

    Args:
        table_rows: Table rows from the index table.
        index_content: Index content from index page.

    Returns:
        Metadata of files to be migrated.
    """
    index_doc = _index_file_from_content(content=index_content)
    table_docs = _extract_docs_from_table_rows(table_rows=table_rows)
    return itertools.chain((index_doc,), table_docs)


def _assert_migration_success(migration_reports: typing.Iterable[types_.ActionReport]) -> None:
    """Assert all documents have been successfully migrated.

    Args:
        migration_results: Report containing migration details from server to local repository.

    Returns:
        None if success, raises MigrationError otherwise.
    """
    if any(result for result in migration_reports if result.result is types_.ActionResult.FAIL):
        raise exceptions.MigrationError(
            "Error migrating the docs, please check the logs for more detail."
        )


def run(
    table_rows: typing.Iterable[types_.TableRow],
    index_content: str,
    discourse: Discourse,
    docs_path: Path,
) -> None:
    """Write document content to docs_path.

    Args:
        table_rows: Iterable sequence of documentation structure to be migrated.
        discourse: Client to the documentation server.
        docs_path: The path to the docs directory containing all the documentation.

    Raises:
        MigrationError if any migration error occurred during migration.

    Returns:
        Migration result reports containing action result and failure reason if any.
    """
    migration_reports = (
        _run_one(file_meta=document, discourse=discourse, docs_path=docs_path)
        for document in _get_docs_metadata(table_rows=table_rows, index_content=index_content)
    )
    _assert_migration_success(migration_reports=migration_reports)
