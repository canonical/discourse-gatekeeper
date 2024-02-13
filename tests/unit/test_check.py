# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for check."""

import logging
from typing import NamedTuple, cast

import pytest

from src import check, constants, repository, types_

from .. import factories
from .helpers import assert_substrings_in_string


def _track_paths_with_diff_parameters():
    """Generate parameters for the track_paths_with_diff test.

    Returns:
        The test parameters, the first item of each element is the action and the second and third
        the expected paths with base and local and base and server diffs, respectively.
    """
    return [
        pytest.param((), (), (), id="empty"),
        pytest.param((factories.UpdateGroupActionFactory(),), (), (), id="single group"),
        pytest.param(
            (factories.UpdateExternalRefActionFactory(),), (), (), id="single external ref"
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base=(base_1 := "base 1"), local=base_1, server=base_1
                    )
                ),
            ),
            (),
            (),
            id="single no diff",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base=(base_1 := "base 1"), local="local 1", server=base_1
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (check.format_path(path_1),),
            (),
            id="single base local diff",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base=(base_1 := "base 1"), local=base_1, server="server 1"
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (),
            (check.format_path(path_1),),
            id="single base server diff",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 1", local=(local_1 := "local 1"), server=local_1
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (),
            (),
            id="single base diff server local same",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 1", local="local 1", server="server 1"
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (check.format_path(path_1),),
            (check.format_path(path_1),),
            id="single all diff",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base=None, local="local 1", server="server 1"
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (),
            (),
            id="single all diff base None",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 1", local="local 1", server="server 1"
                    ),
                    path=(path_1 := ("path 1",)),
                ),
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 2", local="local 2", server="server 2"
                    ),
                    path=(path_2 := ("path 2",)),
                ),
            ),
            (check.format_path(path_1), check.format_path(path_2)),
            (check.format_path(path_1), check.format_path(path_2)),
            id="multiple all diff",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 1", local=(local_1 := "local 1"), server=local_1
                    )
                ),
                factories.UpdatePageActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 2", local=(local_2 := "local 2"), server=local_2
                    )
                ),
            ),
            (),
            (),
            id="multiple base diff local server same",
        ),
    ]


@pytest.mark.parametrize(
    "actions, expected_base_local_diffs, expected_base_server_diffs",
    _track_paths_with_diff_parameters(),
)
def test_track_paths_with_diff(
    actions: tuple[types_.UpdateAction, ...],
    expected_base_local_diffs: tuple[str, ...],
    expected_base_server_diffs: tuple[str, ...],
):
    """
    arrange: given actions
    act: when the actions and passed to TrackPathsWithDiff sequentually
    assert: then the TrackPathsWithDiff has the expected base_local_diffs and base_server_diffs.
    """
    paths_with_diff = check.get_path_with_diffs(actions)

    assert paths_with_diff.base_local_diffs == expected_base_local_diffs
    assert paths_with_diff.base_server_diffs == expected_base_server_diffs


class ExpectedProblem(NamedTuple):
    """
    Attrs:
        path: The expected path.
        description_contents: The expected contents of the description
    """

    path: str
    description_contents: tuple[str, ...]


def _test_conflicts_parameters():
    """Generate parameters for the test_conflicts test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), id="empty"),
        pytest.param((factories.CreatePageActionFactory(),), (), id="single create"),
        pytest.param((factories.NoopPageActionFactory(),), (), id="single noop"),
        pytest.param((factories.DeletePageActionFactory(),), (), id="single delete"),
        pytest.param((factories.UpdateGroupActionFactory(),), (), id="single group update"),
        pytest.param(
            (factories.UpdateExternalRefActionFactory(),),
            (),
            id="single external ref update",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base=None, server="a", local="a")
                ),
            ),
            (),
            id="single update no base content same",
        ),
        pytest.param(
            (
                action_1 := factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base=None, server="a", local="b")
                ),
            ),
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
                    description_contents=(
                        "cannot",
                        "execute",
                        "branch",
                        "discourse",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
            ),
            id="single update no base content different",
        ),
        pytest.param(
            (
                factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base="a", server="a", local="a")
                ),
            ),
            (),
            id="single update no conflict",
        ),
        pytest.param(
            (
                action_1 := factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="c")
                ),
            ),
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
            ),
            id="single update conflict",
        ),
        pytest.param(
            (factories.NoopPageActionFactory(), factories.NoopPageActionFactory()),
            (),
            id="multiple actions no problems",
        ),
        pytest.param(
            (
                action_1 := factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="c")
                ),
                factories.NoopPageActionFactory(),
            ),
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple actions single problem first",
        ),
        pytest.param(
            (
                factories.NoopPageActionFactory(),
                action_2 := factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base="x", server="y", local="z")
                ),
            ),
            (
                ExpectedProblem(
                    path="/".join(action_2.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_2.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple actions single problem second",
        ),
        pytest.param(
            (
                action_1 := factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="c")
                ),
                action_2 := factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base="x", server="y", local="z")
                ),
            ),
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
                ExpectedProblem(
                    path="/".join(action_2.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_2.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple actions multiple problems",
        ),
        pytest.param(
            (
                action_1 := factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="a")
                ),
                action_2 := factories.UpdatePageActionFactory(
                    content_change=types_.ContentChange(base="x", server="x", local="y")
                ),
            ),
            (
                ExpectedProblem(
                    path="/".join(action_2.path),
                    description_contents=(
                        "detected",
                        "unmerged",
                        "community contributions",
                        "/".join(action_1.path),
                        "/".join(action_2.path),
                    ),
                ),
            ),
            id=(
                "multiple actions one has base and local other has local and server diff, tag "
                "applied"
            ),
        ),
    ]


@pytest.mark.parametrize(
    "actions, expected_problems",
    _test_conflicts_parameters(),
)
def test_conflicts(
    actions: tuple[types_.AnyAction, ...],
    expected_problems: tuple[ExpectedProblem],
    caplog: pytest.LogCaptureFixture,
    repository_client: repository.Client,
):
    """
    arrange: given actions
    act: when conflicts is called with the actions
    assert: then the expected problems are yielded.
    """
    caplog.set_level(logging.INFO)

    user_inputs = factories.UserInputsFactory(commit_sha=repository_client.current_commit)
    returned_problems = tuple(
        check.conflicts(
            actions=actions,
            repository=repository_client,
            user_inputs=user_inputs,
        )
    )

    assert len(returned_problems) == len(expected_problems)
    for returned_problem, expected_problem in zip(returned_problems, expected_problems):
        assert returned_problem.path == expected_problem.path
        assert_substrings_in_string(
            expected_problem.description_contents, returned_problem.description
        )
        assert_substrings_in_string(
            (
                "problem",
                "preventing",
                "execution",
                returned_problem.path,
                returned_problem.description,
            ),
            caplog.text,
        )


def _test_external_refs_parameters():
    """Generate parameters for the test_external_refs test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), id="empty"),
        pytest.param(
            (factories.IndexContentsListItemFactory(reference_value="https://canonical.com"),),
            (),
            id="single valid link",
        ),
        pytest.param(
            (
                factories.IndexContentsListItemFactory(
                    reference_value=(path_1 := "https://invalid.link.com")
                ),
            ),
            (
                ExpectedProblem(
                    path=path_1,
                    description_contents=("unable", "connect", "exception"),
                ),
            ),
            id="single invalid link connection error",
        ),
        pytest.param(
            (
                factories.IndexContentsListItemFactory(
                    reference_value=(path_1 := "https://canonica.com/invalid-page")
                ),
            ),
            (
                ExpectedProblem(
                    path=path_1,
                    description_contents=("broken", "link", "404"),
                ),
            ),
            id="single invalid link 404",
        ),
        pytest.param(
            (
                factories.IndexContentsListItemFactory(
                    reference_value=(path_1 := "https://canonica.com/invalid-page-1")
                ),
                factories.IndexContentsListItemFactory(reference_value="https://canonical.com"),
            ),
            (
                ExpectedProblem(
                    path=path_1,
                    description_contents=("broken", "link", "404"),
                ),
            ),
            id="multiple first invalid",
        ),
        pytest.param(
            (
                factories.IndexContentsListItemFactory(reference_value="https://canonical.com"),
                factories.IndexContentsListItemFactory(
                    reference_value=(path_2 := "https://canonica.com/invalid-page-2")
                ),
            ),
            (
                ExpectedProblem(
                    path=path_2,
                    description_contents=("broken", "link", "404"),
                ),
            ),
            id="multiple second invalid",
        ),
        pytest.param(
            (
                factories.IndexContentsListItemFactory(
                    reference_value=(path_1 := "https://invalid.url.com")
                ),
                factories.IndexContentsListItemFactory(
                    reference_value=(path_2 := "https://canonica.com/invalid-page-2")
                ),
            ),
            (
                ExpectedProblem(
                    path=path_1,
                    description_contents=("unable", "connect", "exception"),
                ),
                ExpectedProblem(
                    path=path_2,
                    description_contents=("broken", "link", "404"),
                ),
            ),
            id="multiple invalid",
        ),
        pytest.param(
            (
                factories.IndexContentsListItemFactory(reference_value="https://canonical.com"),
                factories.IndexContentsListItemFactory(
                    reference_value="https://canonical.com/blog"
                ),
            ),
            (),
            id="multiple valid links",
        ),
    ]


@pytest.mark.parametrize(
    "index_contents, expected_problems",
    _test_external_refs_parameters(),
)
def test_external_refs(
    index_contents: tuple[types_.IndexContentsListItem, ...],
    expected_problems: tuple[ExpectedProblem],
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given index_contents
    act: when external_refs is called with the list items
    assert: then the expected problems are yielded.
    """
    caplog.set_level(logging.INFO)

    returned_problems = tuple(check.external_refs(index_contents=index_contents))

    assert len(returned_problems) == len(expected_problems)
    for returned_problem, expected_problem in zip(returned_problems, expected_problems):
        assert returned_problem.path == expected_problem.path
        assert_substrings_in_string(
            expected_problem.description_contents, returned_problem.description
        )
        assert_substrings_in_string(
            (
                "problem",
                "contents",
                "index",
                "row",
                returned_problem.path,
                returned_problem.description,
            ),
            caplog.text,
        )
