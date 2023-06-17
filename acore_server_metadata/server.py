# -*- coding: utf-8 -*-

import typing as T
import dataclasses
from datetime import timezone

from simple_aws_ec2.api import Ec2Instance
from simple_aws_rds.api import RDSDBInstance

from .exc import (
    ServerNotFoundError,
    ServerNotUniqueError,
    ServerAlreadyExistsError,
)
from .settings import settings
from .utils import get_utc_now


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
        该方法是本模块最常用的方法之一. 用例如下:

        .. code-block:: python

            >>> server = Server.get_server("prod", ec2_client, rds_client)
            >>> server
            Server(
                id='prod-1',
                ec2_inst=Ec2Instance(
                    id='i-eb5ffe7acc68a252c',
                    status='running',
                    ...
                    tags={'realm': 'prod-1'},
                    data=...
                ),
                rds_inst=RDSDBInstance(
                    id='db-inst-1',
                    status='available',
                    tags={'realm': 'prod-1'},
                    data=...
                ),
            )

        如果你想要手动创建一个抽象对象而不立刻尝试获得 Server 的信息, 而是想之后再获取,
        你可以这样:

        .. code-block:: python

            >>> server = Server(id="prod")
            >>> server.refresh(ec2_client, rds_client)

        """
        ec2_inst = cls.get_ec2(ec2_client, id)
        if ec2_inst is None:
            return None
        rds_inst = cls.get_rds(rds_client, id)
        if rds_inst is None:  # pragma: no cover
            return None
        return cls(id=id, ec2_inst=ec2_inst, rds_inst=rds_inst)

    @classmethod
    def batch_get_server(
        cls,
        ids: T.List[str],
        ec2_client,
        rds_client,
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
        id_set = set(ids)

        # batch get data
        ec2_inst_list = Ec2Instance.from_tag_key_value(
            ec2_client,
            key=settings.ID_TAG_KEY,
            value=ids,
        ).all()
        rds_inst_list = list()
        for rds_inst in RDSDBInstance.query(rds_client):
            if (
                rds_inst.tags.get(settings.ID_TAG_KEY, "THIS_IS_IMPOSSIBLE_TO_MATCH")
                in id_set
            ):
                rds_inst_list.append(rds_inst)

        # group by server id
        ec2_inst_mapper = dict()
        for ec2_inst in ec2_inst_list:
            key = ec2_inst.tags[settings.ID_TAG_KEY]
            try:
                ec2_inst_mapper[key].append(ec2_inst)
            except KeyError:
                ec2_inst_mapper[key] = [ec2_inst]

        rds_inst_mapper = dict()
        for rds_inst in rds_inst_list:
            key = rds_inst.tags[settings.ID_TAG_KEY]
            try:
                rds_inst_mapper[key].append(rds_inst)
            except KeyError:
                rds_inst_mapper[key] = [rds_inst]

        # merge data
        server_mapper = dict()
        for id in ids:
            ec2_inst_list = ec2_inst_mapper.get(id, [])
            if len(ec2_inst_list) >= 2:
                raise ServerNotUniqueError(f"Found multiple EC2 instance with id {id}")
            elif len(ec2_inst_list) == 0:
                server_mapper[id] = None
                continue
            else:
                ec2_inst = ec2_inst_list[0]

            rds_inst_list = rds_inst_mapper.get(id, [])
            if len(rds_inst_list) >= 2:  # pragma: no cover
                raise ServerNotUniqueError(f"Found multiple RDS instance with id {id}")
            elif len(rds_inst_list) == 0:  # pragma: no cover
                server_mapper[id] = None
                continue
            else:
                rds_inst = rds_inst_list[0]

            server_mapper[id] = cls(id=id, ec2_inst=ec2_inst, rds_inst=rds_inst)

        return server_mapper

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

    # --------------------------------------------------------------------------
    # Operations
    # --------------------------------------------------------------------------
    def run_ec2(
        self,
        ec2_client,
        ami_id: str,
        instance_type: str,
        key_name: str,
        subnet_id: str,
        security_group_ids: T.List[str],
        iam_instance_profile_arn: str,
        tags: T.Optional[T.Dict[str, str]] = None,
        check_exists: bool = True,
    ):
        """
        Launch a new EC2 instance as the Game server from the AMI.
        The configurations are already optimized for the Game server.

        Reference:

        - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/run_instances.html

        :param ec2_client: boto3 ec2 client
        :param ami_id: example: "ami-1a2b3c4d"
        :param instance_type: example "t3.small", "t3.medium", "t3.large", "t3.xlarge", "t3.2xlarge
        :param key_name: example "my-key-pair"
        :param subnet_id: example "subnet-1a2b3c4d"
        :param security_group_ids: example ["sg-1a2b3c4d"]
        :param iam_instance_profile_arn: example "arn:aws:iam::123456789012:instance-profile/my-iam-role"
        :param tags: custom tags
        :param check_exists: if True, check if the EC2 instance already exists
        """
        if check_exists:
            ec2_inst = self.get_ec2(ec2_client, id=self.id)
            if ec2_inst is not None:
                raise ServerAlreadyExistsError(
                    f"EC2 instance {self.id!r} already exists"
                )
        if tags is None:
            tags = dict()
        tags["Name"] = self.id
        tags[settings.ID_TAG_KEY] = self.id  # the realm tag indicator has to match
        tags["tech:machine_creator"] = "acore_server_metadata"
        ec2_client.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            # only launch one instance for each realm
            MinCount=1,
            MaxCount=1,
            KeyName=key_name,
            SecurityGroupIds=security_group_ids,
            SubnetId=subnet_id,
            IamInstanceProfile=dict(Arn=iam_instance_profile_arn),
            TagSpecifications=[
                dict(
                    ResourceType="instance",
                    Tags=[dict(Key=k, Value=v) for k, v in tags.items()],
                ),
            ],
        )

    def run_rds(
        self,
        rds_client,
        db_snapshot_identifier: str,
        db_instance_class: str,
        db_subnet_group_name: str,
        security_group_ids: T.List[str],
        multi_az: bool = False,
        allocated_storage: int = 20,
        tags: T.Optional[T.Dict[str, str]] = None,
        check_exists: bool = True,
    ):
        """
        Launch a new RDS DB instance from the backup snapshot.
        The configurations are already optimized for the Game server.

        Reference:

        - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds/client/restore_db_instance_from_db_snapshot.html

        :param rds_client: boto3 rds client
        :param db_snapshot_identifier: example "my-db-snapshot"
        :param db_instance_class: example "db.t4g.micro", "db.t4g.small", "db.t4g.medium", "db.t4g.large"
        :param db_subnet_group_name: example "my-db-subnet-group"
        :param security_group_ids: example ["sg-1a2b3c4d"]
        :param multi_az: use single instance for dev, multi-az for prod.
        :param allocated_storage: use 20GB (the minimal value you can use) for dev
            use larger volume based on players for prod.
        :param tags: custom tags
        :param check_exists: if True, check if the RDS DB instance already exists
        """
        if check_exists:
            rds_inst = self.get_rds(rds_client, id=self.id)
            if rds_inst is not None:
                raise ServerAlreadyExistsError(
                    f"RDS DB instance {self.id!r} already exists"
                )
        if tags is None:
            tags = dict()
        tags[settings.ID_TAG_KEY] = self.id
        tags["tech:machine_creator"] = "acore_server_metadata"
        rds_client.restore_db_instance_from_db_snapshot(
            DBInstanceIdentifier=self.id,
            DBSnapshotIdentifier=db_snapshot_identifier,
            DBInstanceClass=db_instance_class,
            MultiAZ=multi_az,
            DBSubnetGroupName=db_subnet_group_name,
            AllocatedStorage=allocated_storage,
            PubliclyAccessible=False,  # you should never expose your database to the public
            AutoMinorVersionUpgrade=False,  # don't update MySQL minor version, PLEASE!
            VpcSecurityGroupIds=security_group_ids,
            Tags=[dict(Key=k, Value=v) for k, v in tags.items()],
        )

    def associate_eip_address(
        self,
        ec2_client,
        allocation_id: str,
        check_exists: bool = True,
    ):
        """
        Associate the given Elastic IP address with the EC2 instance.
        Note that this operation is idempotent, it will disassociate and re-associate
        the Elastic IP address if it is already associated with another EC2 instance
        or this one, and each association will incur a small fee. So I would like
        to check before doing this.

        :param ec2_client: boto3 ec2 client
        :param allocation_id: the EIP allocation id, not the pulibc ip,
            example "eipalloc-1a2b3c4d"
        :param check_exists: check if the EC2 instance exists before associating.
        """
        if check_exists:
            ec2_inst = self.get_ec2(ec2_client, id=self.id)
            if ec2_inst is None:
                raise ServerAlreadyExistsError(
                    f"EC2 instance {self.id!r} does not exist"
                )
            self.ec2_inst = ec2_inst
        # check if this allocation id is already associated with an instance
        res = ec2_client.describe_addresses(AllocationIds=[allocation_id])
        address_data = res["Addresses"][0]
        public_id = address_data["PublicIp"]
        instance_id = address_data.get("InstanceId", "invalid-instance-id")
        if instance_id == self.ec2_inst.id:
            return  # already associated
        ec2_client.associate_address(
            AllocationId=allocation_id,
            InstanceId=self.ec2_inst.id,
        )

    def create_db_snapshot(
        self,
        rds_client,
        check_exists: bool = True,
    ):
        """
        Create a 'manual' DB snapshot for the RDS DB instance.
        It use the server id and timestamp as the snapshot id.
        """
        if check_exists:
            rds_inst = self.get_rds(rds_client, id=self.id)
            if rds_inst is None:
                raise ServerNotFoundError(f"RDS DB instance {self.id!r} does not exist")
        now = get_utc_now()
        snapshot_id = "{}-{}".format(
            self.id,
            now.strftime("%Y-%m-%d-%H-%M-%S"),
        )
        rds_client.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=self.rds_inst.id,
            Tags=[
                dict(Key=settings.ID_TAG_KEY, Value=self.id),
                dict(Key="tech:machine_creator", Value="acore_server_metadata"),
            ],
        )

    def cleanup_db_snapshot(
        self,
        rds_client,
        keep_n: int = 3,
        keep_days: int = 365,
    ):
        """
        Clean up old RDS DB snapshots of this server.

        :param rds_client: boto3 rds client
        :param keep_n: keep the latest N snapshots. this criteria has higher priority.
            for example, even the only N snapshots is very very old, but we still keep them.
        :param keep_days: delete snapshots older than N days if we have more than N snapshots.

        todo: use paginator
        """
        # get the list of manual created snapshots
        res = rds_client.describe_db_snapshots(
            DBInstanceIdentifier=self.rds_inst.id,
            SnapshotType="manual",
            MaxRecords=100,
        )
        # sort them by create time, latest comes first
        snapshot_list = list(
            sorted(
                res.get("DBSnapshots", []),
                key=lambda d: d["SnapshotCreateTime"],
                reverse=True,
            )
        )
        if len(snapshot_list) <= keep_n:
            return
        now = get_utc_now()
        for snapshot in snapshot_list[keep_n:]:
            create_time = snapshot["SnapshotCreateTime"]
            create_time = create_time.replace(tzinfo=timezone.utc)
            if (now - create_time).total_seconds() > (keep_days * 86400):
                rds_client.delete_db_snapshot(
                    DBSnapshotIdentifier=snapshot["DBSnapshotIdentifier"],
                )
