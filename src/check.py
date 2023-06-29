# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for running checks."""

import logging
from collections.abc import Iterable, Iterator
from itertools import chain, tee
from typing import NamedTuple, TypeGuard

from . import constants, content
from .constants import DOCUMENTATION_TAG
from .repository import Client
from .types_ import AnyAction, UpdateAction, UserInputs


class Problem(NamedTuple):
    """Details about a failed check.

    Attrs:
        path: Unique identifier for the file and discourse topic with the problem
        description: A summary of what the problem is and how to resolve it.

    """

    path: str
    description: str


format_path = "/".join


class PathsWithDiff(NamedTuple):
    """Keeps track of paths that have any differences.

    Attrs:
        base_local_diffs: The paths that have a difference between the base and local content.
        base_server_diffs: The paths that have a difference between the local and server content.
    """

    base_local_diffs: tuple[str, ...]
    base_server_diffs: tuple[str, ...]


def get_path_with_diffs(actions: Iterable[UpdateAction]) -> PathsWithDiff:
    """Generate the paths that have either local or server content changes.

    Args:
        actions: The update actions to track diffs for.

    Returns:
        The paths that have differences.
    """
    # Filter any actions without a change in content or None base or same local and server content
    actions_with_changes = (
        action
        for action in actions
        if action.content_change is not None
        and action.content_change.base is not None
        and action.content_change.local != action.content_change.server
    )
    # The access to optional attributes is safe because of the filter above, mypy doesn't track
    # to this degree
    # Need an iterator for both attributes
    base_local_actions, base_server_actions = tee(actions_with_changes)
    return PathsWithDiff(
        base_local_diffs=tuple(
            format_path(action.path)
            for action in base_local_actions
            if action.content_change.base != action.content_change.local  # type: ignore
        ),
        base_server_diffs=tuple(
            format_path(action.path)
            for action in base_server_actions
            if action.content_change.base != action.content_change.server  # type: ignore
        ),
    )


def _is_update_action(action: AnyAction) -> TypeGuard[UpdateAction]:
    """Check whether an action is an UpdateAction.

    Args:
        action: The action to check.

    Returns:
        Whether the action is an UpdateAction.
    """
    return isinstance(action, UpdateAction)


def _update_action_problem(action: UpdateAction) -> Problem | None:
    """Get any problem with an update action.

    Args:
        action: The action to check.

    Returns:
        None if there is no problem or the problem if there is an issue with the action.
    """
    if action.content_change is None:
        return None

    if (
        action.content_change.base is None
        and action.content_change.server == action.content_change.local
    ):
        return None

    if action.content_change.base is None:
        diff = content.diff(action.content_change.server, action.content_change.local)
        problem = Problem(
            path=format_path(action.path),
            description=(
                "cannot execute the update action due to not finding a file on the "
                f"{DOCUMENTATION_TAG} tag and there are differences between the branch and "
                "discourse content, please ensure that there are no differences and try again. "
                f"Detected differences:\n{diff}"
            ),
        )
    else:
        action_conflicts = content.conflicts(
            base=action.content_change.base,
            theirs=action.content_change.server,
            ours=action.content_change.local,
        )
        if action_conflicts is None:
            return None
        problem = Problem(
            path=format_path(action.path),
            description=(
                "cannot execute the update action due to conflicting changes on discourse, "
                f"please resolve the conflicts and try again: \n{action_conflicts}"
            ),
        )

    logging.error(
        (
            "there is a problem preventing the execution of an action\npath: %s\nproblem: %s\n"
            "action: %s"
        ),
        problem.path,
        problem.description,
        action,
    )
    return problem


def conflicts(
    actions: Iterable[AnyAction], repository: Client, user_inputs: UserInputs
) -> Iterator[Problem]:
    """Check whether actions have any content conflicts.

    There are two types of conflicts. The first is where the local content is different to what is
    on the server and both the local content and the server content is different from the base.
    This means that there were edits on the server which have not been merged into git and the PR
    is making changes to the same page.

    The second type of conflict is a logical conflict which arises out of that there are at least
    some changes on the server that have not been merged into git yet and the branch is proposing
    to make changes to the documentation as well. This means that there could be changes made on
    the server which logically conflict with proposed changes in the PR. These conflicts can be
    supppressed using the discourse-ahead-ok tag on the commit that the action is running on.

    Args:
        actions: The actions to check.
        repository: Client for repository interactions.
        user_inputs: Configuration from the user.

    Yields:
        A problem for each action with a conflict
    """
    # Need an iterator to check page by page and logical conflicts
    actions_page_conflicts, actions_logical_conflicts = tee(filter(_is_update_action, actions))

    any_page_conflicts = False
    for problem in filter(
        None, (_update_action_problem(action) for action in actions_page_conflicts)
    ):
        any_page_conflicts = True
        yield problem

    # Skip reporting potential logical conflicts if there were any page conflicts
    if any_page_conflicts:
        return

    commit_discourse_ahead_ok_tagged = repository.is_same_commit(
        tag=constants.DISCOURSE_AHEAD_TAG, commit=user_inputs.commit_sha
    )
    if commit_discourse_ahead_ok_tagged:
        return

    paths_with_diff = get_path_with_diffs(actions_logical_conflicts)
    if not paths_with_diff.base_local_diffs or not paths_with_diff.base_server_diffs:
        return

    problem = Problem(
        path=paths_with_diff.base_local_diffs[0],
        description=(
            "detected unmerged community contributions, these need to be resolved "
            "before proceeding. If the differences are not conflicting, please apply the "
            f"{constants.DISCOURSE_AHEAD_TAG} tag to commit {user_inputs.commit_sha} to "
            "proceed. Paths with potentially unmerged community contributions: "
            f"{set(chain(paths_with_diff.base_local_diffs, paths_with_diff.base_server_diffs))}."
        ),
    )
    logging.error(
        "there is a problem preventing the execution of an action\npath: %s\nproblem: %s",
        problem.path,
        problem.description,
    )
    yield problem
