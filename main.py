# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Main execution for the action."""

import os


def main():
    """Execute the action."""
    create_new_input = os.environ["INPUT_CREATE_NEW_TOPIC"]
    print(create_new_input)


if __name__ == "__main__":
    main()
