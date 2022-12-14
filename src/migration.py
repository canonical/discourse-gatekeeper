# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for transforming index table rows into local files."""

import typing
from pathlib import Path

from . import exceptions, types_
from .discourse import Discourse

EMPTY_DIR_REASON = "<created due to empty directory>"
GITKEEP_FILE = ".gitkeep"


def _validate_row_levels(table_rows: typing.Iterable[types_.TableRow]):
    """Check for invalid row levels.

    Args:
        table_rows: Table rows from the index file.

    Raises:
        InvalidRow exception if invalid row level is encountered.
    """
    level = 0
    for row in table_rows:
        if row.level <= 0:
            raise exceptions.InvalidTableRowError(f"Invalid level {row.level} in {row!=row.level}")
        # Level increase of more than 1 is not possible.
        if row.level > level and (difference := row.level - level) > 1:
            raise exceptions.InvalidTableRowError(
                f"Level difference of {difference} encountered in {row=!r}"
            )
        # Level decrease or same level is fine.
        level = row.level


def _migrate_gitkeep(gitkeep_meta: types_.GitkeepMeta, docs_path: Path):
    """Write gitkeep file to docs directory.

    Args:
        gitkeep_meta: Gitkeep metadata from empty directory table row.
        docs_path: Documentation folder path.

    Returns:
        Migration report for gitkeep file creation.
    """
    path = docs_path / gitkeep_meta.path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return types_.MigrationReport(
        table_row=gitkeep_meta.table_row,
        result=types_.ActionResult.SUCCESS,
        path=path,
        reason=EMPTY_DIR_REASON,
    )


def _migrate_document(document_meta: types_.DocumentMeta, discourse: Discourse, docs_path: Path):
    """Write document file with content to docs directory.

    Args:
        document_meta: Document metadata from directory table row with link.
        discourse: Client to the documentation server.
        docs_path: The path to the docs directory to migrate all the documentation.

    Returns:
        Migration report for document file creation.
    """
    try:
        content = discourse.retrieve_topic(url=document_meta.link)
        path = docs_path / document_meta.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return types_.MigrationReport(
            table_row=document_meta.table_row,
            result=types_.ActionResult.SUCCESS,
            path=path,
            reason=None,
        )
    except exceptions.DiscourseError as exc:
        return types_.MigrationReport(
            table_row=document_meta.table_row,
            result=types_.ActionResult.FAIL,
            path=None,
            reason=str(exc),
        )


def _run_one(
    file_meta: types_.MigrationFileMeta, discourse: Discourse, docs_path: Path
) -> types_.MigrationReport:
    """Write document content relative to docs directory.

    Args:
        file_meta: Migration file metadata corresponding to a row in index table.
        discourse: Client to the documentation server.
        docs_path: The path to the docs directory to migrate all the documentation.

    Returns:
        Migration report containing migration result.
    """
    match type(file_meta):
        case types_.GitkeepMeta:
            assert isinstance(file_meta, types_.GitkeepMeta)
            return _migrate_gitkeep(gitkeep_meta=file_meta, docs_path=docs_path)
        case types_.DocumentMeta:
            assert isinstance(file_meta, types_.DocumentMeta)
            return _migrate_document(
                document_meta=file_meta, discourse=discourse, docs_path=docs_path
            )
        # Edge case that should not be possible.
        case _:  # pragma: no cover
            raise exceptions.MigrationError(
                f"internal error, no implementation for migration file, {file_meta=!r}"
            )


def extract_docs(
    table_rows: typing.Iterable[types_.TableRow],
) -> typing.Iterable[types_.MigrationFileMeta]:
    """Extract necessary migration documents to build docs directory from server.

    Algorithm:
        1.  For each table row:
            1.1. If row level is smaller than current working level:
                1.1.1. Yield GitkeepMeta if last working directory was empty.
                1.1.2. Navigate to parent directory based on current level and row level.
            1.2. If row is a directory:
                1.2.1. Create a virtual directory with given path
                1.2.2. Set created virtual directory as working directory.
            1.3. If row is a file: Yield DocumentMeta
        2. If last table row was a directory and yielded no DocumentMeta, yield GitkeepMeta.

    Args:
        table_rows: Table rows from the index file in the order of directory hierarcy.

    Returns:
        Migration documents with navlink to content.\
            .gitkeep file with no content if empty directory.
    """
    _validate_row_levels(table_rows=table_rows)

    level = 0
    last_dir_has_file = True  # Assume root dir is not empty.
    last_dir_row: types_.TableRow | None = None
    cwd = Path()
    for row in table_rows:
        # Next set of hierarchies, change cwd path
        if row.level <= level:
            if not last_dir_has_file and last_dir_row is not None:
                yield types_.GitkeepMeta(path=cwd / GITKEEP_FILE, table_row=last_dir_row)
            while row.level <= level:
                level -= 1
                cwd = cwd.parent

        # if row is directory, move cwd
        if not row.navlink.link:
            last_dir_has_file = False
            last_dir_row = row
            cwd = cwd / row.path
            level = row.level
        else:
            last_dir_has_file = True
            yield types_.DocumentMeta(
                path=cwd / f"{row.path}.md", link=row.navlink.link, table_row=row
            )

    if not last_dir_has_file and last_dir_row:
        yield types_.GitkeepMeta(path=cwd / GITKEEP_FILE, table_row=last_dir_row)


def run(
    documents: typing.Iterable[types_.MigrationFileMeta], discourse: Discourse, docs_path: Path
) -> typing.Iterable[types_.MigrationReport]:
    """Write document content to docs_path.

    Args:
        documents: metadata about a file to be migrated to local docs directory.
        discourse: Client to the documentation server.
        docs_path: The path to the docs directory containing all the documentation.
    """
    return [
        _run_one(file_meta=document, discourse=discourse, docs_path=docs_path)
        for document in documents
    ]
