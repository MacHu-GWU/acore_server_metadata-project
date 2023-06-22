# -*- coding: utf-8 -*-

import typing as T


if T.TYPE_CHECKING:  # pragma: no cover
    from .server import Server


class ServerStatusMixin:
    def is_exists(self: "Server") -> bool:
        """
        检查 EC2 和 RDS 实例是不是都存在 (什么状态不管).
        """
        not_exists = (self.ec2_inst is None) or (self.rds_inst is None)
        return not not_exists

    def is_running(self: "Server") -> bool:
        """
        检查 EC2 和 RDS 是不是都在运行中 (正在启动但还没有完成则不算). 如果 EC2 或 RDS
        有一个不存在则返回 False.
        """
        if self.is_exists() is False:
            return False
        return self.ec2_inst.is_running() and self.rds_inst.is_available()

    def is_ec2_exists(self: "Server") -> bool:
        """
        检查 EC2 是否存在 (什么状态不管).
        """
        return not (self.ec2_inst is None)

    def is_ec2_running(self: "Server"):
        """
        检查 EC2 是不是在运行中 (正在启动但还没有完成则不算). 如果 EC2 不存在则返回 False.
        """
        if self.ec2_inst is None:
            return False
        return self.ec2_inst.is_running()

    def is_rds_exists(self: "Server") -> bool:
        """
        检查 RDS 是否存在 (什么状态不管).
        """
        return not (self.rds_inst is None)

    def is_rds_running(self: "Server"):
        """
        检查 RDS 是不是在运行中 (正在启动但还没有完成则不算). 如果 RDS 不存在则返回 False.
        """
        if self.rds_inst is None:
            return False
        return self.rds_inst.is_available()
