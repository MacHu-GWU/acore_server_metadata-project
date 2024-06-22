# -*- coding: utf-8 -*-

import typing as T
import dataclasses
from datetime import datetime

from simple_aws_ec2.api import Ec2Instance, EC2InstanceStatusEnum
from simple_aws_rds.api import RDSDBInstance, RDSDBInstanceStatusEnum
from acore_constants.api import TagKey

from ..utils import group_by, get_boto_ses_from_ec2_inside
from ..exc import (
    ServerNotUniqueError,
    ServerStatusError,
    ServerNotFoundError,
    ServerAlreadyExistsError,
    FailedToStartServerError,
    FailedToStopServerError,
)


if T.TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_ec2 import EC2Client
    from mypy_boto3_rds import RDSClient


@dataclasses.dataclass
class Server:
    """
    "Server" 是一个逻辑对象, 它代表着一个 Realm 背后的 EC2 实例游戏服务器 和 RDS 数据库实例.
    这个 "Server" 类是一个状态信息的数据容器, 包含了 EC2 和 RDS 的不可变信息, 例如
    instance id, DB identifier. 也包含了一些可变信息, 例如 EC2 status, DB status, IP 地址等.
    有了 Server 对象, 开发者就可以对 EC2, RDS 的信息进行访问, 并能刷新动态信息, 还能对它们进行
    例如创建, 启动, 关闭, 删除等操作.

    一个 "Server" 必须要有一个 id, 这个 id 的命名规则是 ``{env_name}-{server_name}``,
    其中 ``env_name`` 是环境名, 例如 ``sbx``, ``tst``, ``prd`` 等.
    而 ``server_name`` 则是对人类友好的一些名字, 例如 ``山丘之王``, ``洛萨`` 等. 在
    我们的服务器上我们通常用 ``blue``, ``green`` 这一类的名子.

    按照我们运维魔兽世界服务器的最佳实践, 每一个 Realm 必须要有一个唯一的 id. 例如你的
    魔兽世界服务器大区内有 3 个 realm, 而除了有用于生产环境 (prd) 的 3 个服务器外,
    你还有用于开发和测试的 (sbx) 3 个服务器. 那么这六台服务器的 id 就应该是:
    prd-blue, prd-white, prd-yellow, sbx-blue, sbx-white, sbx-yellow. 而根据
    :ref:`blue-green-deployment` 中提到的蓝绿部署, 我们成对的还有
    prd-green, prd-black, prd-orange, sbx-green, sbx-black, sbx-orange 六台服务器.

    那么我们如何标记哪个 EC2 和 RDS 实例是属于哪个服务器的呢? 按照我们的最佳实践, 我们用
    AWS Resources Tag 来标注这些实例是为哪个 Realm 服务的. 例如我们可以用为每个 EC2 和 RDS
    创建一个叫 ``realm`` 的 tag key. 它所属的服务器 id 是什么, 这个 tag value 就是什么.

    设计这个类的目的是是为了能让这个对象能方便的获取 EC2 和 RDS 的 Metadata, 以及进行
    health check. 基于此我们可以实现对整个 Server 集群 (Fleet) 进行管理, 了解集群中的
    每台机器的状态, 并对它们进行操作.

    .. note::

        这个类是个典型的有状态对象. 里面的属性随着时间会发生变化. 请注意开发时不要将它按照一个
        immutable 的数据容器那样设计.
    """

    id: str = dataclasses.field()
    ec2_inst: T.Optional[Ec2Instance] = dataclasses.field(default=None)
    rds_inst: T.Optional[RDSDBInstance] = dataclasses.field(default=None)

    @property
    def env_name(self) -> str:
        """
        Environment name, e.g. ``sbx``, ``tst``, ``prd``.
        """
        return self.id.split("-", 1)[0]

    @property
    def server_name(self) -> str:
        """
        Server name, e.g. ``blue``, ``green``.
        """
        return self.id.split("-", 1)[1]

    @classmethod
    def _get_existing_ec2(
        cls,
        ec2_client: "EC2Client",
        ids: T.List[str],
    ) -> T.List[Ec2Instance]:
        """
        内部方法, 根据指定 server_id 列表, 批量获得获得所有包含该 Tag 的 EC2 实例.
        常用于用 Batch 的方式批量获得信息, 以减少 API 调用次数.
        """
        return Ec2Instance.query(
            ec2_client=ec2_client,
            filters=[
                dict(Name=f"tag:{TagKey.SERVER_ID}", Values=ids),
                # we don't count terminated instances as existing
                dict(
                    Name="instance-state-name",
                    Values=[
                        EC2InstanceStatusEnum.pending.value,
                        EC2InstanceStatusEnum.running.value,
                        EC2InstanceStatusEnum.stopping.value,
                        EC2InstanceStatusEnum.stopped.value,
                    ],
                ),
            ],
        ).all()

    @classmethod
    def _get_existing_rds(
        cls,
        rds_client: "RDSClient",
        ids: T.List[str],
    ) -> T.List[RDSDBInstance]:
        """
        内部方法, 根据指定 server_id 列表, 批量获得获得所有包含该 Tag 的 RDS 实例.
        常用于用 Batch 的方式批量获得信息, 以减少 API 调用次数.
        """
        res = RDSDBInstance.query(rds_client)
        ids = set(ids)
        return [
            rds_inst
            for rds_inst in res
            # we don't count deleted / failed db instances as existing
            if (
                (
                    rds_inst.status
                    not in [
                        RDSDBInstanceStatusEnum.delete_precheck.value,
                        RDSDBInstanceStatusEnum.deleting.value,
                        RDSDBInstanceStatusEnum.failed.value,
                        RDSDBInstanceStatusEnum.restore_error.value,
                    ]
                )
                and (
                    rds_inst.tags.get(
                        TagKey.SERVER_ID,
                        "THIS_IS_IMPOSSIBLE_TO_MATCH",
                    )
                    in ids
                )
            )
        ]

    @classmethod
    def get_ec2(
        cls,
        ec2_client: "EC2Client",
        id: str,
    ) -> T.Optional[Ec2Instance]:
        """
        尝试获取某个 Server 的 EC2 实例信息. 如果 EC2 "不存在" 则返回 None.
        "不存在" 的含义是这个机器还没有被创建, 或是已经被永久删除了.
        如果机器存在而是处于 "启动中", "停止中" 这一类的情况, 由于这个机器还可以回到
        "运行中" 的状态, 所以被视为 "存在". 而如果我们发现有多台实例都有这个 Tag,
        这一定是业务上出现了什么错误, 所以会抛出异常.

        :param id: server id, ``{env_name}-{server_name}``
        """
        ec2_inst_list = cls._get_existing_ec2(ec2_client=ec2_client, ids=[id])
        if len(ec2_inst_list) > 1:  # pragma: no cover
            raise ServerNotUniqueError(f"Found multiple EC2 instance with id {id}")
        elif len(ec2_inst_list) == 0:
            return None
        else:
            return ec2_inst_list[0]

    @classmethod
    def get_rds(
        cls,
        rds_client: "RDSClient",
        id: str,
    ) -> T.Optional[RDSDBInstance]:
        """
        尝试获取某个 Server 的 RDS 实例信息. 如果 RDS "不存在"则返回 None.
        "不存在" 的含义是这个机器还没有被创建, 或是已经被永久删除了.
        如果机器存在而是处于 "启动中", "停止中" 这一类的情况, 由于这个机器还可以回到
        "运行中" 的状态, 所以被视为 "存在". 而如果我们发现有多台实例都有这个 Tag,
        这一定是业务上出现了什么错误, 所以会抛出异常.

        :param id: server id, ``{env_name}-{server_name}``
        """
        rds_inst_list = cls._get_existing_rds(rds_client=rds_client, ids=[id])
        if len(rds_inst_list) > 1:  # pragma: no cover
            raise ServerNotUniqueError(f"Found multiple RDS instance with id {id}")
        elif len(rds_inst_list) == 0:
            return None
        else:
            return rds_inst_list[0]

    @classmethod
    def from_ec2_inside(
        cls,
        ec2_client: T.Optional["EC2Client"] = None,
        rds_client: T.Optional["RDSClient"] = None,
    ) -> "Server":  # pragma: no cover
        """
        用 "自省" 的方式, 从 EC2 实例内部通过 metadata API 获得自己的 instance id,
        进而获得 Server 的 metadata. 如果这台 EC2 不是一个魔兽世界服务器, 那么将会抛出异常.

        :param ec2_client: optional EC2 client, if not given, will automatically
            create on using EC2 IAM role.
        :param rds_client: optional RDS client, if not given, will automatically
            create on using EC2 IAM role.
        """
        boto_ses = None
        if ec2_client is None:
            boto_ses = get_boto_ses_from_ec2_inside()
            ec2_client = boto_ses.client("ec2")
        if rds_client is None:
            if boto_ses is None:
                boto_ses = get_boto_ses_from_ec2_inside()
            rds_client = boto_ses.client("rds")
        ec2_inst = Ec2Instance.from_ec2_inside(ec2_client)
        server_id = ec2_inst.tags[TagKey.SERVER_ID]
        rds_inst = cls.get_rds(rds_client, server_id)
        return cls(
            id=server_id,
            ec2_inst=ec2_inst,
            rds_inst=rds_inst,
        )

    @classmethod
    def get_server(
        cls,
        id: str,
        ec2_client: "EC2Client",
        rds_client: "RDSClient",
    ) -> "Server":
        """
        尝试获得某个 Server 的 EC2 和 RDS 信息. 这个方法会同时调用 :meth:`Server.get_ec2`
        和 :meth:`Server.get_rds`. 无论 EC2 还是 RDS 存不存在, 它都会返回一个 :class:`Server`
        对象. 如果 EC2 或 RDS 不存在, 那么 ``.ec2_inst`` 或 ``.rds_inst`` 属性的值可能是 None.
        关于 "不存在" 的定义请参考 :meth:`Server.get_ec2` 和 :meth:`Server.get_rds`.

        该方法是本模块最常用的方法之一. 用例如下:

        .. code-block:: python

            >>> server = Server.get_server("prd-1", ec2_client, rds_client)
            >>> server
            Server(
                id='prd-1',
                ec2_inst=Ec2Instance(
                    id='i-eb5ffe7acc68a252c',
                    status='running',
                    ...
                    tags={'realm': 'prd-1'},
                    data=...
                ),
                rds_inst=RDSDBInstance(
                    id='db-inst-1',
                    status='available',
                    tags={'realm': 'prd-1'},
                    data=...
                ),
            )

        这个方法只会返回被调用时的 EC2 和 RDS 状态. 如果你要获得它们的最新状态, 请使用
        :meth:`Server.refresh` 方法.
        """
        return cls(
            id=id,
            ec2_inst=cls.get_ec2(ec2_client, id),
            rds_inst=cls.get_rds(rds_client, id),
        )

    @classmethod
    def batch_get_server(
        cls,
        ids: T.List[str],
        ec2_client: "EC2Client",
        rds_client: "RDSClient",
    ) -> T.Dict[str, T.Optional["Server"]]:
        """
        类似于 :meth:`Server.get_server`, 但是可以批量获取多个 Server 的信息, 减少
        API 调用次数.

        用例:

        .. code-block:: python

            >>> server_mapper = Server.batch_get_server(
            ...     ids=["prod-1", "prod-2", "dev-1", "dev-2"],
            ...     ec2_client=ec2_client,
            ...     rds_client=rds_client,
            ... )
            >>> server_mapper
            {
                "prod-1": <Server id="prod-1">,
                "prod-2": <Server id="prod-2">,
                "dev-1": <Server id="dev-1">,
                "dev-2": <Server id="dev-2">,
            }
        """
        # batch get data
        ec2_inst_list = cls._get_existing_ec2(ec2_client=ec2_client, ids=ids)
        rds_inst_list = cls._get_existing_rds(rds_client=rds_client, ids=ids)

        # group by server id
        ec2_inst_mapper = group_by(
            ec2_inst_list, key=lambda inst: inst.tags[TagKey.SERVER_ID]
        )
        rds_inst_mapper = group_by(
            rds_inst_list, key=lambda inst: inst.tags[TagKey.SERVER_ID]
        )

        # merge data
        def get_inst(key: str, mapper: T.Dict[str, list]):
            if key not in mapper:
                return None
            items = mapper[key]
            if len(items) > 1:
                raise ServerNotUniqueError(
                    f"Found multiple {items[0].__class__.__name__} with id {key}"
                )
            else:
                return items[0]

        server_mapper = {
            id: Server(
                id=id,
                ec2_inst=get_inst(id, ec2_inst_mapper),
                rds_inst=get_inst(id, rds_inst_mapper),
            )
            for id in ids
        }
        return server_mapper

    def refresh(
        self,
        ec2_client: "EC2Client",
        rds_client: "RDSClient",
    ):
        """
        重新获取 EC2 和 RDS 实例的信息. 刷新当前类的 ``ec2_inst`` 和 ``rds_inst`` 属性.
        """
        self.ec2_inst = self.get_ec2(ec2_client, self.id)
        self.rds_inst = self.get_rds(rds_client, self.id)

    # --------------------------------------------------------------------------
    # Check server status
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
        检查 EC2 是否存在 (我们不在乎它是什么状态).
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
        检查 RDS 是否存在 (我们不在乎它是什么状态).
        """
        return not (self.rds_inst is None)

    def is_rds_running(self):
        """
        检查 RDS 是不是在运行中 (正在启动但还没有完成则不算). 如果 RDS 不存在则返回 False.
        """
        if self.rds_inst is None:
            return False
        return self.rds_inst.is_available()

    # --------------------------------------------------------------------------
    # Ensure server status
    # --------------------------------------------------------------------------
    def ensure_ec2_exists(self):
        """
        Raises an exception if EC2 instance for this server does not exist.
        """
        if self.is_ec2_exists() is False:
            raise ServerNotFoundError(f"EC2 instance for {self.id!r} server not found!")

    def ensure_ec2_not_exists(self):
        """
        Raises an exception if EC2 instance for this server already exists.
        """
        if self.is_ec2_exists():
            raise ServerAlreadyExistsError(
                f"EC2 instance for {self.id!r} server already exists!"
            )

    def ensure_rds_exists(self):
        """
        Raises an exception if RDS instance for this server does not exist.
        """
        if self.is_rds_exists() is False:
            raise ServerNotFoundError(f"RDS instance for {self.id!r} server not found!")

    def ensure_rds_not_exists(self):
        """
        Raises an exception if RDS instance for this server already exists.
        """
        if self.is_rds_exists():
            raise ServerAlreadyExistsError(
                f"RDS instance for {self.id!r} server already exists!"
            )

    def ensure_ec2_is_running(self):
        """
        Raises an exception if EC2 instance for this server is not running.
        """
        self.ensure_ec2_exists()
        if self.is_ec2_running() is False:
            raise ServerStatusError(
                f"EC2 instance for {self.id!r} server is not running!"
            )

    def ensure_ec2_is_ready_to_start(self):
        """
        Raises an exception if EC2 instance for this server is not ready to start.
        """
        self.ensure_ec2_exists()
        if self.ec2_inst.is_ready_to_start() is False:
            raise FailedToStartServerError(
                f"EC2 instance for {self.id!r} server is not ready to start!"
            )

    def ensure_ec2_is_ready_to_stop(self):
        """
        Raises an exception if EC2 instance for this server is not ready to stop.
        """
        self.ensure_ec2_exists()
        if self.ec2_inst.is_ready_to_stop() is False:
            raise FailedToStopServerError(
                f"EC2 instance for {self.id!r} server is not ready to stop!"
            )

    def ensure_rds_is_running(self):
        """
        Raises an exception if RDS instance for this server is not running.
        """
        self.ensure_rds_exists()
        if self.is_rds_running() is False:
            raise ServerStatusError(
                f"RDS instance for {self.id!r} server is not running!"
            )

    def ensure_rds_is_ready_to_start(self):
        """
        Raises an exception if RDS instance for this server is not ready to start.
        """
        self.ensure_rds_exists()
        if self.rds_inst.is_ready_to_start() is False:
            raise FailedToStartServerError(
                f"RDS instance for {self.id!r} server is not ready to start!"
            )

    def ensure_rds_is_ready_to_stop(self):
        """
        Raises an exception if RDS instance for this server is not ready to stop.
        """
        self.ensure_rds_exists()
        if self.rds_inst.is_ready_to_stop() is False:
            raise FailedToStopServerError(
                f"RDS instance for {self.id!r} server is not ready to stop!"
            )

    @property
    def server_lifecycle(self) -> T.Optional[str]:
        """
        尝试从 EC2 实例的 Tags 中获取 Server 的生命周期状态. 如果没有找到则返回 None.
        """
        if self.ec2_inst is None:  # pragma: no cover
            return None
        return self.ec2_inst.tags.get(TagKey.SERVER_LIFECYCLE)

    @property
    def wow_status(self) -> T.Optional[str]:
        """
        尝试从 EC2 实例的 Tags 中获取魔兽世界服务器 Server 的状态. 如果没有找到则返回 None.
        """
        if self.ec2_inst is None:  # pragma: no cover
            return None
        return self.ec2_inst.tags.get(TagKey.WOW_STATUS)

    @property
    def wow_status_measure_time(self) -> T.Optional[datetime]:
        """
        尝试从 EC2 实例的 Tags 中获取魔兽世界服务器 Server 的状态的测量时间. 如果没有找到则返回 None.
        """
        if self.ec2_inst is None:  # pragma: no cover
            return None
        v = self.ec2_inst.tags.get(TagKey.WOW_STATUS_MEASURE_TIME)
        if v:  # pragma: no cover
            return datetime.fromisoformat(v)
        else:
            return None
