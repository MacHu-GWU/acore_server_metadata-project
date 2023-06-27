# -*- coding: utf-8 -*-

import typing as T
import itertools
from datetime import datetime, timezone

try:
    import boto3
except ImportError:
    pass

from simple_aws_ec2 import Ec2Instance


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


def get_boto_ses_from_ec2_inside() -> "boto3.session.Session":
    aws_region = Ec2Instance.get_placement_region()
    return boto3.session.Session(region_name=aws_region)
