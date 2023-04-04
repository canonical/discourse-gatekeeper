# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Functions that support writing output."""

import os
from pathlib import Path


def write(text: str) -> None:
    """Write text to the GitHub output file.

    Args:
        text: The content to write to the GitHub output.
    """
    github_output = os.getenv("GITHUB_OUTPUT")
    assert github_output, (
        "the GITHUB_OUTPUT environment variable is empty or defined, "
        "is this running in a GitHub workflow?"
    )
    output_file = Path(github_output)
    output_file.write_text(text, encoding="utf-8")
