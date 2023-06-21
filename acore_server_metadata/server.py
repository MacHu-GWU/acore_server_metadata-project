# -*- coding: utf-8 -*-

import typing as T
import dataclasses
from datetime import timezone

from simple_aws_ec2.api import Ec2Instance, EC2InstanceStatusEnum
from simple_aws_rds.api import RDSDBInstance, RDSDBInstanceStatusEnum

from .vendor.hashes import hashes
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
    def _get_existing_ec2(
        cls,
        ec2_client,
        ids: T.List[str],
    ) -> T.List[Ec2Instance]:
        return Ec2Instance.query(
            ec2_client=ec2_client,
            filters=[
                dict(Name=f"tag:{settings.ID_TAG_KEY}", Values=ids),
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
        rds_client,
        ids: T.List[str],
    ) -> T.List[RDSDBInstance]:
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
                        settings.ID_TAG_KEY,
                        "THIS_IS_IMPOSSIBLE_TO_MATCH",
                    )
                    in ids
                )
            )
        ]

    @classmethod
    def get_ec2(
        cls,
        ec2_client,
        id: str,
    ) -> T.Optional[Ec2Instance]:
        """
        尝试获取某个 Server 的 EC2 实例信息. 如果 EC2 "不存在" 则返回 None.
        "不存在" 的含义是这个机器没有被创建, 或是已经被永久删除了. 如果机器存在而是出于启动中,
        停止中这一类的情况, 这个机器还可以被重新启动, 所以被视为存在.
        """
        ec2_inst_list = cls._get_existing_ec2(ec2_client=ec2_client, ids=[id])
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
        尝试获取某个 Server 的 RDS 实例信息. 如果 RDS "不存在"则返回 None.
        "不存在" 的含义是这个数据库没有被创建, 或是已经被永久删除了. 如果机器存在而是出于启动中,
        停止中这一类的情况, 这个数据库还可以被重新启动, 所以被视为存在.
        """
        rds_inst_list = cls._get_existing_rds(rds_client=rds_client, ids=[id])
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
        尝试获得某个 Server 的 EC2 和 RDS 信息, 如果任意一个 "不存在" 则返回 None.
        关于 "不存在" 的定义请参考 :meth:`Server.get_ec2` 和 :meth:`Server.get_rds`.
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

        如果你需要分开判断 EC2 和 RDS 的存在性, 你可以这样:

        .. code-block:: python

            >>> server = Server(id="prod")
            >>> server.refresh(ec2_client, rds_client)
            >>> server.is_ec2_exists()
            True
            >>> server.is_rds_exists()
            False
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
        # batch get data
        ec2_inst_list = cls._get_existing_ec2(ec2_client=ec2_client, ids=ids)
        rds_inst_list = cls._get_existing_rds(rds_client=rds_client, ids=ids)

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
        重新获取 EC2 和 RDS 实例的信息. 刷新当前类的 ``ec2_inst`` 和 ``rds_inst`` 属性.
        """
        self.ec2_inst = self.get_ec2(ec2_client, self.id)
        self.rds_inst = self.get_rds(rds_client, self.id)

    def _get_db_snapshot_id(self) -> str:
        """
        Get the db snapshot id for this server, the snapshot id
        naming convention is "${server_id}-%Y-%m-%d-%H-%M-%S".
        """
        now = get_utc_now()
        snapshot_id = "{}-{}".format(
            self.id,
            now.strftime("%Y-%m-%d-%H-%M-%S"),
        )
        return snapshot_id

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
        **kwargs,
    ):
        """
        Launch a new EC2 instance as the Game server from the AMI.
        The mandatory arguments match how we launch a new WOW server.

        在服务器运维过程中, 我们都是从自己构建的游戏服务器 AMI 启动 EC2 实例. 它的 Tag 必须
        要符合一定的规则 (详情请参考 :class:`Server`). 本方法会自动为新的 EC2 实例打上这些
        必要的 Tag.

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
            **kwargs,
        )

    create_ec2 = run_ec2  # alias

    def run_rds(
        self,
        rds_client,
        db_snapshot_identifier: str,
        db_instance_class: str,
        db_subnet_group_name: str,
        security_group_ids: T.List[str],
        multi_az: bool = False,
        tags: T.Optional[T.Dict[str, str]] = None,
        check_exists: bool = True,
        **kwargs,
    ):
        """
        Launch a new RDS DB instance from the backup snapshot.
        The mandatory arguments match how we launch a new WOW database.

        在数据库运维过程中, 我们都是从自己备份的 Snapshot 启动 DB 实例. 它的 Tag 必须
        要符合一定的规则 (详情请参考 :class:`Server`). 本方法会自动为新的 DB 实例打上这些
        必要的 Tag.

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

        res = rds_client.describe_db_snapshots(
            DBSnapshotIdentifier=db_snapshot_identifier,
        )
        db_snapshot_list = res.get("DBSnapshots", [])
        if len(db_snapshot_list):
            db_snapshot_tags = {
                dct["Key"]: dct["Value"]
                for dct in db_snapshot_list[0].get("TagList", [])
            }
            master_password_digest = db_snapshot_tags.get("tech:master_password_digest")
            if master_password_digest:
                tags["tech:master_password_digest"] = master_password_digest

        rds_client.restore_db_instance_from_db_snapshot(
            DBInstanceIdentifier=self.id,
            DBSnapshotIdentifier=db_snapshot_identifier,
            DBInstanceClass=db_instance_class,
            MultiAZ=multi_az,
            DBSubnetGroupName=db_subnet_group_name,
            PubliclyAccessible=False,  # you should never expose your database to the public
            AutoMinorVersionUpgrade=False,  # don't update MySQL minor version, PLEASE!
            VpcSecurityGroupIds=security_group_ids,
            CopyTagsToSnapshot=True,
            Tags=[dict(Key=k, Value=v) for k, v in tags.items()],
            **kwargs,
        )

    create_rds = run_rds  # alias

    def start_ec2(self, ec2_client):
        """
        Start the EC2 instance of this server.
        """
        self.ec2_inst.start_instance(ec2_client)

    def start_rds(self, rds_client):
        """
        Start the RDS DB instance of this server.
        """
        self.rds_inst.start_db_instance(rds_client)

    def stop_ec2(self, ec2_client):
        """
        Stop the EC2 instance of this server.
        """
        self.ec2_inst.stop_instance(ec2_client)

    def stop_rds(self, rds_client):
        """
        Stop the RDS DB instance of this server.
        """
        self.rds_inst.stop_db_instance(rds_client)

    def delete_ec2(self, ec2_client):
        """
        Delete the EC2 instance of this server.
        """
        self.ec2_inst.terminate_instance(ec2_client)

    def delete_rds(self, rds_client, create_final_snapshot: bool = True):
        """
        Delete the RDS DB instance of this server.

        :param create_final_snapshot: if True, then create a final snapshot
            before deleting the DB instance. and keep automated backups.
            if False, then will not create final snapshot, and also delete
            automated backups.
        """
        if create_final_snapshot:
            snapshot_id = self._get_db_snapshot_id()
            self.rds_inst.delete_db_instance(
                rds_client=rds_client,
                skip_final_snapshot=False,
                final_db_snapshot_identifier=snapshot_id,
                delete_automated_backups=False,
            )
        else:
            self.rds_inst.delete_db_instance(
                rds_client=rds_client,
                skip_final_snapshot=True,
                delete_automated_backups=True,
            )

    def associate_eip_address(
        self,
        ec2_client,
        allocation_id: str,
        check_exists: bool = True,
    ) -> T.Optional[dict]:
        """
        Associate the given Elastic IP address with the EC2 instance.
        Note that this operation is idempotent, it will disassociate and re-associate
        the Elastic IP address if it is already associated with another EC2 instance
        or this one, and each association will incur a small fee. So I would like
        to check before doing this.

        当对生产服务器进行运维时, 我们需要维护给每个服务器一个固定 IP. 我们可以通过定义一个
        映射表, 然后用这个方法确保每个服务器的 IP 是正确的 (该方法是幂等的, 如果已经设置好了
        则什么也不会做).

        Reference:

        - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_addresses.html
        - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/associate_address.html

        :param ec2_client: boto3 ec2 client
        :param allocation_id: the EIP allocation id, not the pulibc ip,
            example "eipalloc-1a2b3c4d"
        :param check_exists: check if the EC2 instance exists before associating.

        :return: if we actually send the ``rds_client.associate_address`` API,
            it returns the response of that API. Otherwise, it returns None.
        """
        if check_exists:
            ec2_inst = self.get_ec2(ec2_client, id=self.id)
            if ec2_inst is None:
                raise ServerAlreadyExistsError(
                    f"EC2 instance {self.id!r} does not exist"
                )
        else:
            ec2_inst = self.ec2_inst

        # check if this allocation id is already associated with an instance
        res = ec2_client.describe_addresses(AllocationIds=[allocation_id])
        address_data = res["Addresses"][0]
        instance_id = address_data.get("InstanceId", "invalid-instance-id")
        if instance_id == ec2_inst.id:  # already associated
            return None

        # associate eip address
        return ec2_client.associate_address(
            AllocationId=allocation_id,
            InstanceId=ec2_inst.id,
        )

    def update_db_master_password(
        self,
        rds_client,
        master_password: str,
        check_exists: bool = True,
    ) -> T.Optional[str]:
        """
        Update the DB instance master password. When you recover the DB instance
        from a snapshot, the master password is the same as the password when you
        create the snapshot. This method can be used to update the master password.

        在数据库运维过程中, 我们都是从自己备份的 Snapshot 启动 DB 实例. 它的管理员密码会继承
        备份 Snapshot 的时候的密码. 比如我们希望用开发环境的 snapshot 创建生产环境的数据库,
        这时候再继续用开发环境的密码肯定不妥, 所以需要更新密码. 该方法可以做到这一点.
        并且这个方法是幂等的, 如果密码已经设置好了, 则什么也不会做. 如果密码没有被设置过, 则
        会设置密码.

        :return: if we actually send the ``rds_client.modify_db_instance`` API,
            it returns the response of that API. Otherwise, it returns None.
        """
        if check_exists:
            rds_inst = self.get_rds(rds_client, id=self.id)
            if rds_inst is None:
                raise ServerNotFoundError(f"RDS DB instance {self.id!r} does not exist")
        else:
            rds_inst = self.rds_inst

        hashes.use_sha256()
        master_password_digest = hashes.of_str(master_password, hexdigest=True)
        if (
            rds_inst.tags.get("tech:master_password_digest", "invalid")
            == master_password_digest
        ):
            # do nothing
            return None

        response = rds_client.modify_db_instance(
            DBInstanceIdentifier=rds_inst.id,
            MasterUserPassword=master_password,
            ApplyImmediately=True,
        )

        rds_client.add_tags_to_resource(
            ResourceName=rds_inst.db_instance_arn,
            Tags=[
                dict(Key="tech:master_password_digest", Value=master_password_digest)
            ],
        )

        return response

    def create_db_snapshot(
        self,
        rds_client,
        check_exists: bool = True,
    ):
        """
        Create a 'manual' DB snapshot for the RDS DB instance.
        The snapshot id naming convention is "${server_id}-%Y-%m-%d-%H-%M-%S".

        在数据库运维过程中, 我们需要定期备份生产服务器的数据库. 该方法能为我们创建 DB snapshot
        并合理明明, 打上对应的 Tag.
        """
        if check_exists:
            rds_inst = self.get_rds(rds_client, id=self.id)
            if rds_inst is None:
                raise ServerNotFoundError(f"RDS DB instance {self.id!r} does not exist")
        else:
            rds_inst = self.rds_inst

        snapshot_id = self._get_db_snapshot_id()
        rds_client.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=rds_inst.id,
            Tags=[
                dict(Key=settings.ID_TAG_KEY, Value=rds_inst.id),
                dict(Key="tech:machine_creator", Value="acore_server_metadata"),
            ],
        )

    def cleanup_db_snapshot(
        self,
        rds_client,
        keep_n: int = 3,
        keep_days: int = 365,
    ) -> T.Optional[T.List[dict]]:
        """
        Clean up old RDS DB snapshots of this server.

        在数据库运维过程中, 我们需要定期备份生产服务器的数据库. 该方法能为我们创建 DB snapshot
        并合理明明, 打上对应的 Tag.

        :param rds_client: boto3 rds client
        :param keep_n: keep the latest N snapshots. this criteria has higher priority.
            for example, even the only N snapshots is very very old, but we still keep them.
        :param keep_days: delete snapshots older than N days if we have more than N snapshots.

        todo: use paginator to list existing snapshots

        :return: if we actually send the ``rds_client.delete_db_snapshot`` API,
            it returns the list of response of that API. Otherwise, it returns None.
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
            return None
        now = get_utc_now()
        response_list = []
        for snapshot in snapshot_list[keep_n:]:
            create_time = snapshot["SnapshotCreateTime"]
            create_time = create_time.replace(tzinfo=timezone.utc)
            if (now - create_time).total_seconds() > (keep_days * 86400):
                response = rds_client.delete_db_snapshot(
                    DBSnapshotIdentifier=snapshot["DBSnapshotIdentifier"],
                )
                response_list.append(response)
        return response_list
