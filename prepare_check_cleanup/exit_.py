# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Functions that exit the e2e test process."""

import sys


def with_result(check_result: bool) -> None:
    """Exit and set exit code based on the check result.

    Args:
        check_result: The outcome of a check.
    """
    sys.exit(0 if check_result else 1)
