# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for transforming index table rows into local files."""

import typing
from pathlib import Path

from . import exceptions, types_

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
            raise exceptions.InvalidTableRowLevelError(
                f"Invalid level {row.level} in {row!=row.level}"
            )
        # Level increase of more than 1 is not possible.
        if row.level > level and (difference := row.level - level) > 1:
            raise exceptions.InvalidTableRowLevelError(
                f"Level difference of {difference} encountered in {row=!r}"
            )
        # Level decrease or same level is fine.
        level = row.level


def migrate(
    table_rows: typing.Iterable[types_.TableRow],
) -> typing.Iterable[types_.MigrationDocument]:
    """Create migration documents to migrate from server.

    Args:
        table_rows: Table rows from the index file in the order of directory hierarcy.
        docs_path: Docs directory base path.

    Returns:
        Migration documents with navlink to content.\
            .gitkeep file with no content if empty directory.
    """
    _validate_row_levels(table_rows=table_rows)

    level = 0
    last_dir_has_file = True
    cwd = Path()
    for row in table_rows:
        # Next set of hierarchies, change cwd path
        if row.level <= level:
            if not last_dir_has_file:
                yield types_.GitkeepFile(path=cwd / GITKEEP_FILE)
            while row.level <= level:
                level -= 1
                cwd = cwd.parent

        # if row is directory, move cwd
        if not row.navlink.link:
            last_dir_has_file = False
            cwd = cwd / row.path
            level = row.level
        else:
            last_dir_has_file = True
            yield types_.DocumentFile(path=cwd / f"{row.path}.md", link=row.navlink.link)

    if not last_dir_has_file:
        yield types_.GitkeepFile(path=cwd / GITKEEP_FILE)
