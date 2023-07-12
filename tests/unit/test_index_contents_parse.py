# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for index module _get_contents_parsed_items function."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from itertools import chain

import pytest

from src import exceptions, index, types_

from .. import factories
from .helpers import assert_substrings_in_string


def _test__get_contents_parsed_items_invalid_parameters():
    """Generate parameters for the test__get_contents_parsed_items_invalid test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            f"""# Contents
{(line := '-')}""",
            (line,),
            id="first item only leader",
        ),
        pytest.param(
            f"""# Contents
{(line := '- [title 1]')}""",
            (line,),
            id="first item leader and reference title",
        ),
        pytest.param(
            f"""# Contents
{(line := '- [title 1(value 1)')}""",
            (line,),
            id="first item malformed reference title",
        ),
        pytest.param(
            f"""# Contents
{(line := '- [title 1](value 1')}""",
            (line,),
            id="first item malformed reference value",
        ),
        pytest.param(
            f"""# Contents
{(line := '- [title 1] (value 1)')}""",
            (line,),
            id="first item space between reference title and value",
        ),
        pytest.param(
            f"""# Contents
{(line := ' - [title 1](value 1)')}""",
            (line,),
            id="first item has single leading space",
        ),
        pytest.param(
            f"""# Contents
{(line := '  - [title 1](value 1)')}""",
            (line,),
            id="first item has multiple leading space",
        ),
        pytest.param(
            f"""# Contents
{(line := '- [title 1](value 1)other')}""",
            (line,),
            id="first item trailing non-whitespace",
        ),
        pytest.param(
            f"""# Contents
{(line := 'malformed')}""",
            (line,),
            id="single malformed line",
        ),
        pytest.param(
            f"""# Contents
- [title 1](value 1)
{(line := 'malformed')}""",
            (line,),
            id="multiple lines single malformed line second",
        ),
        pytest.param(
            f"""# Contents
{(line := 'malformed')}
- [title 1](value 1)""",
            (line,),
            id="multiple lines single malformed line first",
        ),
        pytest.param(
            f"""# Contents
{(line := 'malformed 1')}
malformed 2""",
            (line,),
            id="multiple malformed lines",
        ),
        pytest.param(
            f"""# Contents
- [title 1](value 1)
{(line := '1 [title 1](value 1)')}""",
            (line,),
            id="multiple lines second missing leader",
        ),
        pytest.param(
            f"""# Contents
- [title 1](value 1)
{(line := 'maformed [title 1](value 1)')}""",
            (line,),
            id="multiple lines second missing leader alternate",
        ),
    ]


@pytest.mark.parametrize(
    "content, expected_message_contents",
    _test__get_contents_parsed_items_invalid_parameters(),
)
def test__get_contents_parsed_items_invalid(
    content: str, expected_message_contents: tuple[str, ...]
):
    """
    arrange: given the index file contents which are invalid
    act: when get_contents_list_items is called with the index file
    assert: then InputError is raised with the expected contents in the message.
    """
    index_file = types_.IndexFile(title="title 1", content=content)

    with pytest.raises(exceptions.InputError) as exc_info:
        tuple(index._get_contents_parsed_items(index_file=index_file))

    assert_substrings_in_string(
        chain(
            expected_message_contents,
            "invalid",
            "item",
            "contents",
            "index",
            index.DOCUMENTATION_INDEX_FILENAME,
        ),
        str(exc_info.value).lower(),
    )


def _test__get_contents_parsed_items_parameters():
    """Generate parameters for the test__get_contents_parsed_items test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            None,
            (),
            id="missing file",
        ),
        pytest.param(
            "",
            (),
            id="empty file",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item",
        ),
        pytest.param(
            f"""# Contents

- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item new line between header and start",
        ),
        pytest.param(
            f"""# Contents
-  [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item multiple whitespace after leader",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')}) """,
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item trailing whitespace",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})  """,
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item multiple trailing whitespace",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item empty line before",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item empty line after",
        ),
        pytest.param(
            f"""# Contents
1. [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item numbered",
        ),
        pytest.param(
            f"""# Contents
10. [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item numbered multiple digits",
        ),
        pytest.param(
            f"""# Contents
a. [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item alphabetical",
        ),
        pytest.param(
            f"""# Contents
ab. [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item alphabetical multiple letters",
        ),
        pytest.param(
            f"""# Contents
* [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item star",
        ),
        pytest.param(
            f"""# Other content
- [other title 1](other value 1)
# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item content before",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
# Other content
- [other title 1](other value 1)
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item content after",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
# Contents
- [other title 1](other value 1)
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
            ),
            id="single item content after with duplicate heading",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
- [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_2, reference_value=value_2, rank=1
                ),
            ),
            id="multiple items flat",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_title=title_2, reference_value=value_2, rank=1
                ),
            ),
            id="multiple items nested",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
 - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1, reference_title=title_2, reference_value=value_2, rank=1
                ),
            ),
            id="multiple items nested alternate spacing single space",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
- [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_2, reference_value=value_2, rank=1
                ),
            ),
            id="multiple items empty line middle",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  1. [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_title=title_2, reference_value=value_2, rank=1
                ),
            ),
            id="multiple items nested alternate leader",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
- [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
- [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_2, reference_value=value_2, rank=1
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_3, reference_value=value_3, rank=2
                ),
            ),
            id="many items flat",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
- [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_title=title_2, reference_value=value_2, rank=1
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_3, reference_value=value_3, rank=2
                ),
            ),
            id="many items second nested",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
- [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
  - [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_2, reference_value=value_2, rank=1
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_title=title_3, reference_value=value_3, rank=2
                ),
            ),
            id="many items last nested",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
  - [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_title=title_2, reference_value=value_2, rank=1
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_title=title_3, reference_value=value_3, rank=2
                ),
            ),
            id="many items nested",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
    - [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0, reference_title=title_1, reference_value=value_1, rank=0
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2, reference_title=title_2, reference_value=value_2, rank=1
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=4, reference_title=title_3, reference_value=value_3, rank=2
                ),
            ),
            id="many items deeply nested",
        ),
    ]


@pytest.mark.parametrize("content, expected_items", _test__get_contents_parsed_items_parameters())
def test__get_contents_parsed_items(
    content: str, expected_items: tuple[index._ParsedListItem, ...]
):
    """
    arrange: given the index file contents
    act: when get_contents_list_items is called with the index file
    assert: then the expected contents list items are returned.
    """
    index_file = types_.IndexFile(title="title 1", content=content)

    returned_items = tuple(index._get_contents_parsed_items(index_file=index_file))

    assert returned_items == expected_items
