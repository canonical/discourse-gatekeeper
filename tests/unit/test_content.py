# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for content."""

import pytest

from gatekeeper import content, exceptions

from .helpers import assert_substrings_in_string


def _test_conflicts_parameters():
    """Generate parameters for the test_conflicts test.

    Returns:
        The tests.
    """
    return [
        pytest.param("a", "a", "a", False, id="all same"),
        pytest.param("a", "a", "b", False, id="base and theirs the same"),
        pytest.param("a", "b", "a", False, id="base and ours the same"),
        pytest.param("a", "b", "b", False, id="theirs and ours the same"),
        pytest.param("a", "b", "c", True, id="all different conflict"),
        pytest.param(
            "line 1\nline 2\n line 3\n",
            "line 1a\nline 2\n line 3\n",
            "line 1\nline 2\n line 3a\n",
            True,
            id="all different no git conflict",
        ),
    ]


@pytest.mark.parametrize(
    "base, theirs, ours, expected_conflict",
    _test_conflicts_parameters(),
)
def test_conflicts(base: str, theirs: str, ours: str, expected_conflict: bool):
    """
    arrange: given content for base, theirs and ours
    act: when conflicts is called with the content
    assert: then the expected value is returned.
    """
    result = content.conflicts(base=base, theirs=theirs, ours=ours)

    if not expected_conflict:
        assert result is None
    else:
        assert result is not None
        assert_substrings_in_string(("diff", content.diff(theirs, ours)), result)


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


def _test_diff_parameters():
    """Generate parameters for the test_diff test.

    Returns:
        The tests.
    """
    return [
        pytest.param("a", "a", "  a", id="single line same"),
        pytest.param("a", "x", "- a+ x", id="single line different"),
        pytest.param("a\nb", "a\nb", "  a\n  b", id="multiple line same"),
        pytest.param("a\nb", "x\ny", "- a\n- b+ x\n+ y", id="multiple line different"),
    ]


@pytest.mark.parametrize(
    "first, second, expected_diff",
    _test_diff_parameters(),
)
def test_diff(first: str, second: str, expected_diff: str):
    """
    arrange: given two strings
    act: when diff is called with the strings
    assert: then the expected diff is returned.
    """
    returned_diff = content.diff(first=first, second=second)

    assert returned_diff == expected_diff
