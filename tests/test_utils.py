# -*- coding: utf-8 -*-

import typing as T
import dataclasses
from acore_server_metadata import utils


def test_get_utc_now():
    utils.get_utc_now()


def test_group_by():
    @dataclasses.dataclass
    class User:
        id: int
        name: str

        def user_method(self):
            pass

    lst: T.Iterable[User] = [
        User(1, "a"),
        User(2, "a"),
        User(3, "b"),
        User(4, "b"),
    ]
    groups = utils.group_by(lst, key=lambda x: x.name)
    assert groups["a"][0].id == 1
    assert groups["a"][1].id == 2
    assert groups["b"][0].id == 3
    assert groups["b"][1].id == 4

    users = groups["a"]
    # users.append() # type hint should pop up

    user = users[0]
    # user.user_method()  # type hint should pop up


if __name__ == "__main__":
    from acore_server_metadata.tests import run_cov_test

    run_cov_test(__file__, "acore_server_metadata.utils", preview=False)
