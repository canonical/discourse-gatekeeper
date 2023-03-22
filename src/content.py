# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for checking for 3-way merge conflicts and create content based on a 3 way merge."""

import tempfile
from pathlib import Path

from git.exc import GitCommandError
from git.repo import Repo

from .exceptions import ContentError


def conflicts(base: str, theirs: str, ours: str) -> str | None:
    """Check for merge conflicts based on the git merge algorithm.

    Args:
        base: The starting point for both changes.
        theirs: The other change.
        ours: The local change.

    Returns:
        The description of the merge conflicts or None if there are no conflicts.
    """
    try:
        merge(base=base, theirs=theirs, ours=ours)
    except ContentError as exc:
        return str(exc)
    return None


def merge(base: str, theirs: str, ours: str) -> str:
    """Create the merged content based on the git merge algorithm.

    Args:
        base: The starting point for both changes.
        theirs: The other change.
        ours: The local change.

    Returns:
        The merged content.

    Raises:
        ContentError: if there are merge conflicts.
    """
    # Handle cases that are guaranteed not to have conflicts
    if theirs == base:
        return ours
    if ours == base:
        return theirs
    if theirs == ours:
        return theirs

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialise repository
        tmp_path = Path(tmp_dir)
        repo = Repo.init(tmp_path)
        writer = repo.config_writer()
        writer.set_value("user", "name", "temp_user")
        writer.set_value("user", "email", "temp_email")
        writer.set_value("commit", "gpgsign", "false")
        writer.release()
        base_branch = "base"
        their_branch = "theirs"
        our_branch = "ours"

        # Create base
        repo.git.checkout("-b", base_branch)
        (content_path := tmp_path / "content.txt").write_text(base, encoding="utf-8")
        repo.git.add(".")
        repo.git.commit("-m", "'initial commit'")

        # Create their branch
        repo.git.checkout("-b", their_branch)
        content_path.write_text(theirs, encoding="utf-8")
        repo.git.add(".")
        repo.git.commit("-m", "'their change'")

        # Create our branch
        repo.git.checkout(base_branch)
        repo.git.checkout("-b", our_branch)
        content_path.write_text(ours, encoding="utf-8")
        repo.git.add(".")
        repo.git.commit("-m", "'our change'")

        try:
            repo.git.merge(their_branch)
        except GitCommandError as exc:
            conflicts = content_path.read_text(encoding="utf-8")
            raise ContentError(f"could not automatically merge, conflicts:\n{conflicts}") from exc

        return content_path.read_text(encoding="utf-8")
