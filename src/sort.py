# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Sort items for publishing."""

import itertools
import typing
from pathlib import Path

from more_itertools import peekable, side_effect

from . import types_


class _SortData(typing.NamedTuple):
    """Holds the data structures required for sorting.

    Attrs:
        alpha_sorted_path_infos: PathInfo sorted by alphabetical_rank.
        local_path_yielded: Whether a given local_path of a PathInfo has been yielded.
        local_path_path_info: Lookup from PathInfo.local_path to the PathInfo.
        directories_index: Lookup for the index of the directory PathInfos into
            alpha_sorted_path_infos.
        items: The contents index items.
        docs_path: The directory the documentation files are contained within.
    """

    alpha_sorted_path_infos: list[types_.PathInfo]
    local_path_yielded: dict[Path, bool]
    local_path_path_info: dict[Path, types_.PathInfo]
    directories_index: dict[Path, int]
    items: "peekable[types_.IndexContentsListItem]"
    docs_path: Path


def _create_sort_data(
    path_infos: typing.Iterable[types_.PathInfo],
    index_contents: typing.Iterable[types_.IndexContentsListItem],
    docs_path: Path,
) -> _SortData:
    """Create the data structures required for the sort execution.

    Args:
        path_infos: Information about the local documentation files.
        index_contents: The content index items used to apply sorting.
        docs_path: The directory the documentation files are contained within.

    Returns:
        The data structures required for sorting.
    """
    # Ensure initial sorting is correct
    alpha_sorted_path_infos = sorted(path_infos, key=lambda path_info: path_info.alphabetical_rank)
    rank_sorted_index_contents = sorted(index_contents, key=lambda item: item.rank)

    directories_index = {
        path_info.local_path: idx
        for idx, path_info in enumerate(alpha_sorted_path_infos)
        if path_info.local_path.is_dir()
    }
    directories_index[docs_path] = 0

    return _SortData(
        alpha_sorted_path_infos=alpha_sorted_path_infos,
        local_path_yielded={path_info.local_path: False for path_info in alpha_sorted_path_infos},
        local_path_path_info={
            path_info.local_path: path_info for path_info in alpha_sorted_path_infos
        },
        directories_index=directories_index,
        items=peekable(rank_sorted_index_contents),
        docs_path=docs_path,
    )


def _contents_index_iter(
    sort_data: _SortData,
    current_dir: Path,
    current_hierarchy: int = 0,
) -> typing.Iterator[types_.PathInfo]:
    """Recursively iterates through items by their hierarchy.

    Args:
        sort_data: The input data required for the sorting.
        current_dir: The directory being processed.
        current_hierarchy: The hierarchy of the directory being processed.

    Yields:
        PathInfo in sorted order first by the contents index items and then by alphabetical rank.
    """
    while (next_item := sort_data.items.peek(None)) is not None:
        # Advance iterator
        item = next_item
        # Pass default of None to guarantee StopIteration is not raised
        next(sort_data.items, None)
        next_item = sort_data.items.peek(None)

        # Get the path info
        item_local_path = sort_data.docs_path / item.reference_value
        item_path_info = sort_data.local_path_path_info[item_local_path]
        # Update the navlink title based on the contents index
        item_path_info_dict = item_path_info._asdict()
        item_path_info_dict["navlink_title"] = item.reference_title
        yield types_.PathInfo(**item_path_info_dict)
        sort_data.local_path_yielded[item_local_path] = True

        # Check for directory
        if item_path_info.local_path.is_dir():
            yield from _contents_index_iter(
                sort_data=sort_data,
                current_dir=item_path_info.local_path,
                current_hierarchy=current_hierarchy + 1,
            )

        # Check for last item in the directory
        if next_item is None or next_item.hierarchy <= current_hierarchy:
            # Yield all remaining items for the current directory
            path_infos_for_dir = itertools.takewhile(
                lambda path_info: current_dir in path_info.local_path.parents,
                sort_data.alpha_sorted_path_infos[sort_data.directories_index[current_dir] + 1 :],
            )
            path_infos_for_dir_not_yielded = (
                path_info
                for path_info in path_infos_for_dir
                if not sort_data.local_path_yielded[path_info.local_path]
            )
            yield from side_effect(
                lambda path_info: sort_data.local_path_yielded.update(
                    ((path_info.local_path, True),)
                ),
                path_infos_for_dir_not_yielded,
            )


def using_contents_index(
    path_infos: typing.Iterable[types_.PathInfo],
    index_contents: typing.Iterable[types_.IndexContentsListItem],
    docs_path: Path,
) -> typing.Iterator[types_.PathInfo]:
    """Sort PathInfos based on the contents index and alphabetical rank.

    Also updates the navlink title for any items matched to the contents index.

    Args:
        path_infos: Information about the local documentation files.
        index_contents: The content index items used to apply sorting.
        docs_path: The directory the documentation files are contained within.

    Yields:
        PathInfo sorted based on their location on the contents index and then by alphabetical
        rank.
    """
    sort_data = _create_sort_data(
        path_infos=path_infos, index_contents=index_contents, docs_path=docs_path
    )

    yield from _contents_index_iter(sort_data=sort_data, current_dir=docs_path)
    # Yield all items not yet yielded
    yield from (
        path_info
        for path_info in sort_data.alpha_sorted_path_infos
        if not sort_data.local_path_yielded[path_info.local_path]
    )
