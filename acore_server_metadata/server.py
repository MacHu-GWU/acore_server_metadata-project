# -*- coding: utf-8 -*-

import typing as T
import dataclasses

from simple_aws_ec2.api import Ec2Instance
from simple_aws_rds.api import RDSDBInstance

from .exc import ServerNotFoundError, ServerNotUniqueError
from .settings import settings


@dataclasses.dataclass
class Server:
    """
    代表着一个 Realm 背后的 EC2 实例游戏服务器 和 RDS 数据库实例. 每一个 Realm 必须要有一个
    唯一的 id. 例如你的魔兽世界服务器大区内有 3 个 realm, 而除了有用于生产环境 (prod) 的
    3 个服务器外, 你还有用于开发和测试的 (dev) 3 个服务器. 那么这六台服务器的 id 就应该是:
    prod-1, prod-2, prod-3, dev-1, dev-2, dev-3.

    AWS 上可能有很多 EC2, RDS 实例. 我们需要用 AWS Resources Tag 来标注这些实例是为哪个
    Realm 服务的. 例如我们可以用 tag key 为 "realm" 的 tag 来标注这些实例.

    设计这个类的意义是为了能让这个对象能方便的获取 EC2 和 RDS 的 Metadata, 以及进行
    health check. 最终我们需要对整个 Server 集群进行管理, 了解集群中的每台机器的状态.

    .. note::

        这个类是个典型的有状态对象. 里面的属性随着时间会发生变化. 请注意开发时不要将它按照一个
        immutable 的数据容器那样设计.
    """

    id: str = dataclasses.field()
    ec2_inst: T.Optional[Ec2Instance] = dataclasses.field(default=None)
    rds_inst: T.Optional[RDSDBInstance] = dataclasses.field(default=None)

    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    @classmethod
    def get_ec2(
        cls,
        ec2_client,
        id: str,
    ) -> T.Optional[Ec2Instance]:
        """
        尝试获取某个 Server 的 EC2 实例信息. 如果 EC2 不存在则返回 None.
        """
        res = Ec2Instance.from_tag_key_value(
            ec2_client, key=settings.ID_TAG_KEY, value=id
        )
        ec2_inst_list = res.all()
        if len(ec2_inst_list) > 1:
            raise ServerNotUniqueError(f"Found multiple EC2 instance with id {id}")
        elif len(ec2_inst_list) == 0:
            return None
        else:
            return ec2_inst_list[0]

    @classmethod
    def get_rds(
        cls,
        rds_client,
        id: str,
    ) -> T.Optional[RDSDBInstance]:
        """
        尝试获取某个 Server 的 RDS 实例信息. 如果 RDS 不存在则返回 None.
        """
        res = RDSDBInstance.from_tag_key_value(
            rds_client, key=settings.ID_TAG_KEY, value=id
        )
        rds_inst_list = res.all()
        if len(rds_inst_list) > 1:  # pragma: no cover
            raise ServerNotUniqueError(f"Found multiple RDS instance with id {id}")
        elif len(rds_inst_list) == 0:
            return None
        else:
            return rds_inst_list[0]

    @classmethod
    def get_server(
        cls,
        id: str,
        ec2_client,
        rds_client,
    ) -> T.Optional["Server"]:
        """
        尝试获得某个 Server 的 EC2 和 RDS 信息, 如果任意一个不存在则返回 None.

        如果你想要手动创建一个抽象对象而不立刻尝试获得 Server 的信息, 而是想之后再获取,
        你可以这样:

        .. code-block:: python

            >>> server = Server(id="prod-1")
            >>> server.refresh(ec2_client, rds_client)

        """
        ec2_inst = cls.get_ec2(ec2_client, id)
        if ec2_inst is None:
            return None
        rds_inst = cls.get_rds(rds_client, id)
        if rds_inst is None:  # pragma: no cover
            return None
        return cls(id=id, ec2_inst=ec2_inst, rds_inst=rds_inst)

    # --------------------------------------------------------------------------
    # Check status
    # --------------------------------------------------------------------------
    def is_exists(self) -> bool:
        """
        检查 EC2 和 RDS 实例是不是都存在 (什么状态不管).
        """
        not_exists = (self.ec2_inst is None) or (self.rds_inst is None)
        return not not_exists

    def is_running(self) -> bool:
        """
        检查 EC2 和 RDS 是不是都在运行中 (正在启动但还没有完成则不算). 如果 EC2 或 RDS
        有一个不存在则返回 False.
        """
        if self.is_exists() is False:
            return False
        return self.ec2_inst.is_running() and self.rds_inst.is_available()

    def is_ec2_exists(self) -> bool:
        """
        检查 EC2 是否存在 (什么状态不管).
        """
        return not (self.ec2_inst is None)

    def is_ec2_running(self):
        """
        检查 EC2 是不是在运行中 (正在启动但还没有完成则不算). 如果 EC2 不存在则返回 False.
        """
        if self.ec2_inst is None:
            return False
        return self.ec2_inst.is_running()

    def is_rds_exists(self) -> bool:
        """
        检查 RDS 是否存在 (什么状态不管).
        """
        return not (self.rds_inst is None)

    def is_rds_running(self):
        """
        检查 RDS 是不是在运行中 (正在启动但还没有完成则不算). 如果 RDS 不存在则返回 False.
        """
        if self.rds_inst is None:
            return False
        return self.rds_inst.is_available()

    def refresh(
        self,
        ec2_client,
        rds_client,
    ):
        """
        重新获取 EC2 和 RDS 实例的信息.
        """
        self.ec2_inst = self.get_ec2(ec2_client, self.id)
        self.rds_inst = self.get_rds(rds_client, self.id)
