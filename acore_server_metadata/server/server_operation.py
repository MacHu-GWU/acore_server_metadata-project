# -*- coding: utf-8 -*-

"""
See :class:`ServerOperationMixin` for more details.
"""

import typing as T
from datetime import timezone

from acore_constants.api import TagKey

from ..utils import get_utc_now
from ..exc import (
    ServerNotFoundError,
    ServerAlreadyExistsError,
    FailedToStartServerError,
)
from ..vendor.hashes import hashes

if T.TYPE_CHECKING:  # pragma: no cover
    from .server import Server
    from mypy_boto3_ec2 import EC2Client
    from mypy_boto3_rds import RDSClient


class ServerOperationMixin:
    """
    This mixin provides methods to operate the server ec2 and rds.
    """
    def _get_db_snapshot_id(self: "Server") -> str:
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
        self: "Server",
        ec2_client: "EC2Client",
        ami_id: str,
        instance_type: str,
        key_name: str,
        subnet_id: str,
        security_group_ids: T.List[str],
        iam_instance_profile_arn: str,
        tags: T.Optional[T.Dict[str, str]] = None,
        check_exists: bool = True,
        **kwargs,
    ):  # pragma: no cover
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

        :return: the response from ``rds_client.run_instances``
        """
        if check_exists:
            ec2_inst = self.get_ec2(ec2_client, id=self.id)
            if ec2_inst is not None:  # pragma: no cover
                raise ServerAlreadyExistsError(
                    f"EC2 instance {self.id!r} already exists"
                )
        if tags is None:
            tags = dict()
        tags["Name"] = self.id
        tags[TagKey.SERVER_ID] = self.id  # the realm tag indicator has to match
        tags["tech:machine_creator"] = "acore_server_metadata"
        return ec2_client.run_instances(
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
        self: "Server",
        rds_client: "RDSClient",
        db_snapshot_identifier: str,
        db_instance_class: str,
        db_subnet_group_name: str,
        security_group_ids: T.List[str],
        multi_az: bool = False,
        tags: T.Optional[T.Dict[str, str]] = None,
        check_exists: bool = True,
        **kwargs,
    ):  # pragma: no cover
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

        :return: the response from ``rds_client.restore_db_instance_from_db_snapshot``
        """
        if check_exists:
            rds_inst = self.get_rds(rds_client, id=self.id)
            if rds_inst is not None:  # pragma: no cover
                raise ServerAlreadyExistsError(
                    f"RDS DB instance {self.id!r} already exists"
                )
        if tags is None:
            tags = dict()
        tags[TagKey.SERVER_ID] = self.id
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

        return rds_client.restore_db_instance_from_db_snapshot(
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

    def start_server(
        self: "Server",
        ec2_client: "EC2Client",
        rds_client: "RDSClient",
    ):
        """
        Start a stopped server. Basically it starts the RDS instance first,
        once the RDS instance become available, then start the EC2 instance.
        """
        if self.rds_inst.is_ready_to_start():
            self.start_rds(rds_client)
        elif self.rds_inst.is_available():
            pass
        else:
            raise FailedToStartServerError(
                "RDS instance is not available and also not ready to start"
            )
        self.rds_inst.wait_for_available(
            rds_client,
            delays=10,
            timeout=300,
        )
        if self.ec2_inst.is_ready_to_start():
            self.start_ec2(ec2_client)
        elif self.ec2_inst.is_running():
            pass
        else:
            raise FailedToStartServerError(
                "EC2 instance is not running and also not ready to start"
            )

    def start_ec2(self: "Server", ec2_client: "EC2Client") -> dict:
        """
        Start the EC2 instance of this server.

        :return: the response from ``ec2_client.start_instances``
        """
        return self.ec2_inst.start_instance(ec2_client)

    def start_rds(self: "Server", rds_client: "RDSClient") -> dict:
        """
        Start the RDS DB instance of this server.

        :return: the response from ``rds_client.start_db_instance``
        """
        return self.rds_inst.start_db_instance(rds_client)

    def stop_ec2(self: "Server", ec2_client: "EC2Client") -> dict:
        """
        Stop the EC2 instance of this server.

        :return: the response from ``ec2_client.stop_instances``
        """
        return self.ec2_inst.stop_instance(ec2_client)

    def stop_rds(self: "Server", rds_client: "RDSClient") -> dict:
        """
        Stop the RDS DB instance of this server.

        :return: the response from ``rds_client.stop_db_instance``
        """
        return self.rds_inst.stop_db_instance(rds_client)

    def delete_ec2(self: "Server", ec2_client: "EC2Client"):
        """
        Delete the EC2 instance of this server.

        :return: the response from ``ec2_client.terminate_instances``
        """
        return self.ec2_inst.terminate_instance(ec2_client)

    def delete_rds(
        self: "Server",
        rds_client: "RDSClient",
        create_final_snapshot: bool = True,
    ) -> dict:
        """
        Delete the RDS DB instance of this server.

        :param create_final_snapshot: if True, then create a final snapshot
            before deleting the DB instance. and keep automated backups.
            if False, then will not create final snapshot, and also delete
            automated backups.

        :return: the response from ``rds_client.delete_db_instance``
        """
        if create_final_snapshot:
            snapshot_id = self._get_db_snapshot_id()
            return self.rds_inst.delete_db_instance(
                rds_client=rds_client,
                skip_final_snapshot=False,
                final_db_snapshot_identifier=snapshot_id,
                delete_automated_backups=False,
            )
        else:
            return self.rds_inst.delete_db_instance(
                rds_client=rds_client,
                skip_final_snapshot=True,
                delete_automated_backups=True,
            )

    def associate_eip_address(
        self: "Server",
        ec2_client: "EC2Client",
        allocation_id: str,
        check_exists: bool = True,
        allow_reassociation: bool = False,
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
        :param allow_reassociation: if True, automatically disassociate the EIP
            from the existing instance and associate it with the new instance.

        :return: if we actually send the ``rds_client.associate_address`` API,
            it returns the response of that API. Otherwise, it returns None.
        """
        if check_exists:
            ec2_inst = self.get_ec2(ec2_client, id=self.id)
            if ec2_inst is None:  # pragma: no cover
                raise ServerNotFoundError(f"EC2 instance {self.id!r} does not exist")
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
            AllowReassociation=allow_reassociation,
        )

    def update_db_master_password(
        self: "Server",
        rds_client: "RDSClient",
        master_password: str,
        check_exists: bool = True,
    ) -> T.Optional[dict]:
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
            if rds_inst is None:  # pragma: no cover
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
        self: "Server",
        rds_client: "RDSClient",
        check_exists: bool = True,
    ) -> dict:
        """
        Create a 'manual' DB snapshot for the RDS DB instance.
        The snapshot id naming convention is "${server_id}-%Y-%m-%d-%H-%M-%S".

        在数据库运维过程中, 我们需要定期备份生产服务器的数据库. 该方法能为我们创建 DB snapshot
        并合理明明, 打上对应的 Tag.

        :return: the response of ``rds_client.create_db_snapshot`` API.
        """
        if check_exists:
            rds_inst = self.get_rds(rds_client, id=self.id)
            if rds_inst is None:  # pragma: no cover
                raise ServerNotFoundError(f"RDS DB instance {self.id!r} does not exist")
        else:
            rds_inst = self.rds_inst

        snapshot_id = self._get_db_snapshot_id()
        return rds_client.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=rds_inst.id,
            Tags=[
                dict(Key=TagKey.SERVER_ID, Value=rds_inst.id),
                dict(Key="tech:machine_creator", Value="acore_server_metadata"),
            ],
        )

    def cleanup_db_snapshot(
        self: "Server",
        rds_client: "RDSClient",
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
