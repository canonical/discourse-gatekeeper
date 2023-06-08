# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for running checks."""

import logging
from collections.abc import Iterable, Iterator
from typing import NamedTuple, TypeGuard

from . import content
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


class TrackPathsWithDiff:
    """Keeps track of paths that have any differences.

    Attrs:
        base_local_diffs: The paths that have a difference between the base and local content.
        local_server_diffs: The paths that have a difference between the local and server content.
    """

    def __init__(self) -> None:
        """Construct."""
        self._base_local_diffs = []
        self._local_server_diffs = []

    @property
    def base_local_diffs(self) -> Iterator[str]:
        """Get the paths with base and local diffs."""
        return iter(self._base_local_diffs)

    @property
    def local_server_diffs(self) -> Iterator[str]:
        """Get the paths with local and server diffs."""
        return iter(self._local_server_diffs)

    def process(self, action: UpdateAction) -> None:
        """Record differences for a given action.

        Args:
            action: The update action to process.
        """
        content_change = action.content_change

        if content_change is None:
            return

        if content_change.base != content_change.local:
            self._base_local_diffs.append(action.path)

        if content_change.local != content_change.server:
            self._local_server_diffs.append(action.path)


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
            path="/".join(action.path),
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
            path="/".join(action.path),
            description=(
                "cannot execute the update action due to conflicting changes on discourse, "
                f"please resolve the conflicts and try again: \n{action_conflicts}"
            ),
        )

    logging.error(
        "there is a problem preventing the execution of an action, action: %s, problem: %s",
        action,
        problem,
    )
    return problem


def conflicts(
    actions: Iterable[AnyAction], repository: Client, user_inputs: UserInputs
) -> Iterator[Problem]:
    """Check whether actions have any content conflicts.

    Args:
        actions: The actions to check.

    Yields:
        A problem for each action with a conflict
    """
    update_actions = filter(_is_update_action, actions)
    yield from filter(None, (_update_action_problem(action) for action in update_actions))
