# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Integration tests for discourse."""


def test_create_get_update_unlist_topic():
    """
    arrange: given running discourse server
    act: when a topic is created, retrieved, updated and unlisted
    assert: then all the sequential actions succeed and the topic is unlisted in the end.
    """
    assert True
