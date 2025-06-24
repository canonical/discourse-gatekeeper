# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Execute the uploading of documentation."""

import itertools
import re
import typing
from collections.abc import Iterable
from enum import Enum, auto
from pathlib import Path

from gatekeeper.constants import (
    DOC_FILE_EXTENSION,
    DOCUMENTATION_INDEX_FILENAME,
    NAVIGATION_HEADING,
)
from gatekeeper.discourse import Discourse
from gatekeeper.exceptions import DiscourseError, InputError, ServerError
from gatekeeper.types_ import Index, IndexContentsListItem, IndexFile, Metadata, Page

CONTENTS_HEADER = "# contents"
CONTENTS_END_LINE_PREFIX = "#"

_WHITESPACE = "( *)"
_LEADER = r"((\d+\.)|([a-zA-Z]+\.)|(\*)|(-))"
_REFERENCE_TITLE = r"\[(.*)\]"
_REFERENCE_VALUE = r"\((.*)\)"
_REFERENCE = rf"({_REFERENCE_TITLE}{_REFERENCE_VALUE})"
_ITEM = rf"^{_WHITESPACE}{_LEADER}\s*{_REFERENCE}\s*$"
_ITEM_PATTERN = re.compile(_ITEM)
_HIDDEN_ITEM = _ITEM.replace(r"^", r"^<!-- ").replace(r"$", r" -->$")
_HIDDEN_ITEM_PATTERN = re.compile(_HIDDEN_ITEM)
_COMMENT_ITEM = re.compile(rf"^{_WHITESPACE}<!-- (.+?) -->$")


def _read_docs_index(docs_path: Path) -> str | None:
    """Read the content of the index file.

    Args:
        docs_path: The path to look for the index content.

    Returns:
        The content of the index file if it exists, otherwise return None.

    """
    if not docs_path.is_dir():
        return None
    if not (index_file := docs_path / DOCUMENTATION_INDEX_FILENAME).is_file():
        return None

    return index_file.read_text()


def get(metadata: Metadata, docs_path: Path, server_client: Discourse) -> Index:
    """Retrieve the local and server index information.

    Args:
        metadata: Information about the charm.
        docs_path: The base path to look for the documentation.
        server_client: A client to the documentation server.

    Returns:
        The index page.

    Raises:
        ServerError: if interactions with the documentation server occurs.

    """
    if metadata.docs is not None:
        index_url = metadata.docs
        try:
            server_content = server_client.retrieve_topic(url=index_url)
        except DiscourseError as exc:
            raise ServerError("Index page retrieval failed") from exc
        server = Page(url=index_url, content=server_content)
    else:
        server = None

    name_value = metadata.name
    local_content = _read_docs_index(docs_path=docs_path)
    local = IndexFile(
        title=f"{name_value.replace('-', ' ').title()} Documentation Overview",
        content=local_content,
    )

    return Index(server=server, local=local, name=name_value)


def contents_from_page(page: str) -> str:
    """Get index file contents from server page.

    Args:
        page: Page contents from server.

    Returns:
        Index file contents.
    """
    return "\n".join(
        itertools.takewhile(
            lambda line: line.lower() != f"# {NAVIGATION_HEADING.lower()}", page.splitlines()
        )
    )


class _ParsedListItem(typing.NamedTuple):
    """Represents a parsed item in the contents table.

    Attrs:
        whitespace_count: The number of leading whitespace characters
        reference_title: The name of the reference
        reference_value: The link to the referenced item
        rank: The number of preceding elements in the list
        hidden: Whether the item should be displayed on the navigation table
        comment: Whether the item is a comment
    """

    whitespace_count: int
    reference_title: str
    reference_value: str
    rank: int
    hidden: bool
    comment: bool


def _parse_item_from_line(line: str, rank: int) -> _ParsedListItem:
    """Parse an index list item from a contents line.

    Args:
        line: The contents line to parse.
        rank: The number of previous items.

    Returns:
        The parsed content item.

    Raises:
        InputError:
            - When an item is malformed.
            - When the first item has leading whitespace.
    """
    hidden = False
    if not (match := _ITEM_PATTERN.match(line)):
        match = _HIDDEN_ITEM_PATTERN.match(line)
        hidden = True

    if match is None:
        comment_match = _COMMENT_ITEM.match(line)
        if not comment_match:
            raise InputError(
                f"An item in the contents of the index file at {DOCUMENTATION_INDEX_FILENAME} is "
                f"invalid, {line=!r}, expecting regex: {_ITEM}"
            )
        # Some comments are not part of the indexing and are used for skipping lint checks such as
        # vale checks. e.g. <!-- vale Canonical.004-Canonical-product-names = NO -->
        whitespace_count = len(comment_match.group(1))
        comment_content = comment_match.group(2)
        return _ParsedListItem(
            whitespace_count=whitespace_count,
            reference_title=comment_content,
            reference_value=comment_content,
            rank=rank,
            hidden=hidden,
            comment=True
        )

    whitespace_count = len(match.group(1))

    if not hidden and whitespace_count != 0 and rank == 0:
        raise InputError(
            f"An item in the contents of the index file at {DOCUMENTATION_INDEX_FILENAME} is "
            f"invalid, {line=!r}, expecting the first line not to have any leading whitespace"
        )

    reference_title = match.group(8)
    reference_value = match.group(9)

    return _ParsedListItem(
        whitespace_count=whitespace_count,
        reference_title=reference_title,
        reference_value=reference_value,
        rank=rank,
        hidden=hidden,
        comment=False
    )


class _IndexSection(Enum):
    """The sections of the index file.

    Attrs:
        CONTENTS: The contents section.
        EX_CONTENTS: Everything except the contents section.
    """

    CONTENTS = auto()
    EX_CONTENTS = auto()


def _iter_index_lines(lines: typing.Iterable[str], section: _IndexSection) -> typing.Iterator[str]:
    """Remove the contents section lines from the index contents.

    Args:
        lines: The lines of the index file.
        section: The part of the index file to return lines for.

    Yields:
        All lines except the lines of the contents section.
    """
    contents_encountered = False
    drop_lines = section == _IndexSection.CONTENTS
    for line in lines:
        if not contents_encountered and line.lower() == CONTENTS_HEADER:
            contents_encountered = True
            drop_lines = section == _IndexSection.EX_CONTENTS
        elif line.startswith(CONTENTS_END_LINE_PREFIX):
            drop_lines = section == _IndexSection.CONTENTS

        if not drop_lines:
            yield line


def get_content_for_server(index_file: IndexFile) -> str:
    """Get the contents from the index file that should be passed to the server.

    Args:
        index_file: Information about the local index file.

    Returns:
        The contents of the index file that should be stored on the server.
    """
    if index_file.content is None:
        return ""

    return "\n".join(
        _iter_index_lines(index_file.content.splitlines(), section=_IndexSection.EX_CONTENTS)
    )


def _get_contents_parsed_items(index_file: IndexFile) -> typing.Iterator[_ParsedListItem]:
    """Get the items from the contents list of the index file.

    Args:
        index_file: The index file to read the contents from.

    Yields:
        All the items on the contents list in the index file.
    """
    if index_file.content is None:
        return

    # Get the lines of the contents section
    contents_lines = _iter_index_lines(
        index_file.content.splitlines(), section=_IndexSection.CONTENTS
    )
    # Skip header
    next(contents_lines, None)
    yield from (
        _parse_item_from_line(line=line, rank=rank)
        for line, rank in zip(filter(None, contents_lines), itertools.count())
    )


class ItemReferenceType(Enum):
    """Classification for the path of an item.

    Attrs:
        EXTERNAL: a link to an external resource.
        DIR: a link to a local directory.
        FILE: a link to a local file.
        UNKNOWN: The reference is not a known type.
    """

    EXTERNAL = auto()
    DIR = auto()
    FILE = auto()
    UNKNOWN = auto()


def classify_item_reference(reference: str, docs_path: Path) -> ItemReferenceType:
    """Classify the type of a reference.

    Args:
        reference: The reference to classify.
        docs_path: The parent path of the reference.

    Returns:
        The type of the reference.
    """
    if reference.lower().startswith("http"):
        return ItemReferenceType.EXTERNAL
    if (reference_path := docs_path / Path(reference)).is_dir():
        return ItemReferenceType.DIR
    if reference_path.is_file():
        return ItemReferenceType.FILE
    return ItemReferenceType.UNKNOWN


def _check_contents_item(
    item: _ParsedListItem, max_whitespace: int, aggregate_dir: Path, docs_path: Path
) -> None:
    """Check item is valid. All the items should be exactly within a directory.

    Args:
        item: The parsed item to check.
        max_whitespace: The expected number of whitespace characters for items.
        aggregate_dir: The relative directory that all items must be within.
        docs_path: The base directory of all items.

    Raises:
        InputError:
            - An item has more whitespace than a previous item and it is not following a directory.
            - A nested item is not immediately within the path of its parent.
            - An item isn't a file nor directory.
            - If an item is hidden and is a directory.
    """
    # Check that the whitespace count matches the expectation
    if item.whitespace_count > max_whitespace:
        raise InputError(
            "An item has more whitespace and is not following a reference to a directory. "
            f"{item=!r}, expected whitespace count: {max_whitespace!r}"
        )

    # Check whether item is hidden and a directory
    item_reference_type = classify_item_reference(
        reference=item.reference_value, docs_path=docs_path
    )

    if item.hidden and item_reference_type == ItemReferenceType.DIR:
        raise InputError(f"A hidden item is a directory. {item=!r}")

    if item_reference_type in {ItemReferenceType.DIR, ItemReferenceType.FILE}:
        # Check that the next item is within the directory
        item_relative_path = Path(item.reference_value)
        try:
            item_to_aggregate_path = item_relative_path.relative_to(aggregate_dir)
        except ValueError as exc:
            raise InputError(
                "A nested item is a reference to a path that is not within the directory of its "
                f"parent. {item=!r}, expected parent path: {aggregate_dir!r}"
            ) from exc

        # Check that the item is directly within the current directory
        if len(item_to_aggregate_path.parents) != 1:
            raise InputError(
                "A nested item is a reference to a path that is not immediately within the "
                f"directory of its parent. {item=!r}, expected parent path: {aggregate_dir!r}"
            )

        # Check that if the item is a file, it has the correct extension
        if item_reference_type == ItemReferenceType.FILE:
            if (docs_path / Path(item.reference_value)).suffix.lower() != DOC_FILE_EXTENSION:
                raise InputError(
                    "An item in the contents list is not of the expected file type. "
                    f"{item=!r}, expected extension: {DOC_FILE_EXTENSION}"
                )


def _calculate_contents_hierarchy(
    parsed_items: Iterable[_ParsedListItem],
    docs_path: Path,
    aggregate_dir: Path = Path(),
    hierarchy: int = 0,
) -> typing.Iterator[IndexContentsListItem]:
    """Calculate the hierarchy of the contents list items.

    Args:
        parsed_items: The parsed items from the contents list in the index file.
        docs_path: The base directory of all items.
        aggregate_dir: The relative directory that all items must be within.
        hierarchy: The hierarchy of the current directory.

    Yields:
        The contents list items with the hierarchy.

    Raises:
        InputError:
            - An item has more whitespace than a previous item and it is not following a directory.
            - A nested item is not immediately within the path of its parent.
            - An item isn't a file nor directory.
    """
    parents: list[_ParsedListItem] = []
    whitespace_expectation_per_level = {0: 0}
    parsed_items = iter(parsed_items)
    item = next(parsed_items, None)
    while item:
        # Skip comment lines
        if item.comment:
            item = next(item)
            continue

        # All items in the current directory have been processed
        if item.whitespace_count < whitespace_expectation_per_level[hierarchy]:
            hierarchy = hierarchy - 1
            parent = parents.pop()
            aggregate_dir = Path(parent.reference_value).parent

        _check_contents_item(
            item=item,
            max_whitespace=whitespace_expectation_per_level[hierarchy],
            aggregate_dir=aggregate_dir,
            docs_path=docs_path,
        )

        # Advance the iterator
        item_reference_type = classify_item_reference(
            reference=item.reference_value, docs_path=docs_path
        )
        next_item = next(parsed_items, None)

        if item_reference_type == ItemReferenceType.UNKNOWN:
            raise InputError(
                f"An item is not a file, directory or external HTTP resource. {item=!r}"
            )

        yield IndexContentsListItem(
            hierarchy=hierarchy + 1,
            reference_title=item.reference_title,
            reference_value=item.reference_value,
            rank=item.rank,
            hidden=item.hidden,
        )
        # Process directory contents
        if (
            item_reference_type == ItemReferenceType.DIR
            and next_item is not None
            and next_item.whitespace_count > whitespace_expectation_per_level[hierarchy]
        ):
            hierarchy = hierarchy + 1
            aggregate_dir = Path(item.reference_value)
            if hierarchy not in whitespace_expectation_per_level:
                whitespace_expectation_per_level[hierarchy] = next_item.whitespace_count
            parents.append(item)
        item = next_item


def get_contents(index_file: IndexFile, docs_path: Path) -> typing.Iterator[IndexContentsListItem]:
    """Get the contents list items from the index file.

    Args:
        index_file: The index file to read the contents from.
        docs_path: The base directory of all items.

    Returns:
        Iterator with all items from the contents list.
    """
    parsed_items = _get_contents_parsed_items(index_file=index_file)
    return _calculate_contents_hierarchy(parsed_items=parsed_items, docs_path=docs_path)
