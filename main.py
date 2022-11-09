# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main execution for the action."""

import os


def main():
    """Execute the action."""
    create_new_input = os.environ["INPUT_CREATE_NEW_TOPIC"]
    print(create_new_input)


if __name__ == "__main__":
    main()
