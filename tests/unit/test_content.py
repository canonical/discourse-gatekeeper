# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for content."""

import pytest

from src import content, exceptions

from .helpers import assert_substrings_in_string


def _test_has_conflicts_parameters():
    """Generate parameters for the test_has_conflicts test.

    Returns:
        The tests.
    """
    return [
        pytest.param("a", "a", "a", None, id="all same"),
        pytest.param("a", "a", "b", None, id="base and theirs the same"),
        pytest.param("a", "b", "a", None, id="base and ours the same"),
        pytest.param("a", "b", "b", None, id="theirs and ours the same"),
        pytest.param("a", "b", "c", ("a", "b", "c"), id="all different conflict"),
        pytest.param(
            "line 1\nline 2\n line 3\n",
            "line 1a\nline 2\n line 3\n",
            "line 1\nline 2\n line 3a\n",
            None,
            id="all different no conflict",
        ),
    ]


@pytest.mark.parametrize(
    "base, theirs, ours, expected_contents",
    _test_has_conflicts_parameters(),
)
def test_has_conflicts(
    base: str, theirs: str, ours: str, expected_contents: tuple[str, ...] | None
):
    """
    arrange: given content for base, theirs and ours
    act: when conflicts is called with the content
    assert: then the expected value is returned.
    """
    result = content.conflicts(base=base, theirs=theirs, ours=ours)

    if expected_contents is None:
        assert result is None
    else:
        assert result is not None
        assert_substrings_in_string(
            (*expected_contents, "not", "merge", "<<<<<<< HEAD", ">>>>>>> theirs"), result
        )


def _test_merge_parameters():
    """Generate parameters for the test_merge test.

    Returns:
        The tests.
    """
    return [
        pytest.param("a", "a", "a", "a", id="all same"),
        pytest.param("a", "a", "b", "b", id="base and theirs the same"),
        pytest.param("a", "b", "a", "b", id="base and ours the same"),
        pytest.param("a", "b", "b", "b", id="theirs and ours the same"),
        pytest.param(
            "line 1\nline 2\n line 3\n",
            "line 1a\nline 2\n line 3\n",
            "line 1\nline 2\n line 3a\n",
            "line 1a\nline 2\n line 3a\n",
            id="all different no conflict",
        ),
    ]


@pytest.mark.parametrize(
    "base, theirs, ours, expected_contents",
    _test_merge_parameters(),
)
def test_merge(base: str, theirs: str, ours: str, expected_contents: tuple[str, ...] | None):
    """
    arrange: given content for base, theirs and ours
    act: when merge is called with the content
    assert: then the expected content is returned.
    """
    returned_content = content.merge(base=base, theirs=theirs, ours=ours)

    assert returned_content == expected_contents


def test_merge_conflict():
    """
    arrange: given content for base, theirs and ours with conflicts
    act: when merge is called with the content
    assert: then ContentError is raised.
    """
    base = "a"
    theirs = "b"
    ours = "c"

    with pytest.raises(exceptions.ContentError) as exc_info:
        content.merge(base=base, theirs=theirs, ours=ours)

    assert_substrings_in_string(
        (base, theirs, ours, "not", "merge", "<<<<<<< HEAD", ">>>>>>> theirs"), str(exc_info.value)
    )