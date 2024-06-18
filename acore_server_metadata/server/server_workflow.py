# -*- coding: utf-8 -*-

"""
See :class:`ServerOperationMixin` for more details.
"""

import typing as T

if T.TYPE_CHECKING:  # pragma: no cover
    from .server import Server
    from mypy_boto3_ec2 import EC2Client
    from mypy_boto3_rds import RDSClient


class ServerWorkflowMixin:
    """
    Server Workflow Mixin class that contains all the server workflow methods.
    """
    def test(self: "Server"):
        pass