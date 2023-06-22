# -*- coding: utf-8 -*-

import typing as T
import itertools
from datetime import datetime, timezone


def get_utc_now() -> datetime:
    return datetime.utcnow().replace(tzinfo=timezone.utc)


VT = T.TypeVar("VT")  # value type


def group_by(
    iterable: T.Iterable[VT],
    key: T.Callable[[VT], str],
) -> T.Dict[str, T.List[VT]]:
    return {
        key: list(items)
        for key, items in itertools.groupby(
            iterable,
            key=key,
        )
    }
