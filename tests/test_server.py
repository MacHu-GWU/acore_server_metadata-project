# -*- coding: utf-8 -*-

import typing as T
import moto
import pytest

from simple_aws_ec2.api import Ec2Instance
from simple_aws_rds.api import RDSDBInstance
from acore_constants.api import TagKey

from acore_server_metadata.tests.mock_aws import BaseMockTest
from acore_server_metadata.exc import (
    ServerNotUniqueError,
    ServerStatusError,
    ServerNotFoundError,
    ServerAlreadyExistsError,
    FailedToStartServerError,
    FailedToStopServerError,
)
from acore_server_metadata.server.api import (
    Server,
    ServerNotUniqueError,
)


class TestServer(BaseMockTest):
    mock_list = [
        moto.mock_sts,
        moto.mock_ec2,
        moto.mock_rds,
    ]

    ami_id: T.Optional[str] = None

    @classmethod
    def setup_class_post_hook(cls):
        cls.ami_id = cls.bsm.ec2_client.describe_images()["Images"][0]["ImageId"]

    # --------------------------------------------------------------------------
    # helper methods
    # --------------------------------------------------------------------------
    @property
    def ec2_client(self):
        return self.bsm.ec2_client

    @property
    def rds_client(self):
        return self.bsm.rds_client

    def launch_ec2(self, id: str) -> str:
        """
        :param id: it is the server_id
        :return: ec2 instance id
        """
        ec2_id = self.ec2_client.run_instances(
            MinCount=1,
            MaxCount=1,
            ImageId=self.ami_id,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": TagKey.SERVER_ID, "Value": id},
                    ],
                },
            ],
        )["Instances"][0]["InstanceId"]
        return ec2_id

    def launch_rds(self, id: str) -> str:
        """
        :param id: it is the server_id
        :return: db  instance id
        """
        rds_id = self.rds_client.create_db_instance(
            DBInstanceIdentifier=id,
            DBInstanceClass="db.t2.micro",
            Engine="mysql",
            Tags=[
                {"Key": TagKey.SERVER_ID, "Value": id},
            ],
        )["DBInstance"]["DBInstanceIdentifier"]
        return rds_id

    def delete_all_ec2(self):
        for ec2_inst in Ec2Instance.query(self.ec2_client):
            ec2_inst.terminate_instance(self.ec2_client)

    def delete_all_rds(self):
        for rds_inst in RDSDBInstance.query(self.rds_client):
            rds_inst.delete_db_instance(self.rds_client, skip_final_snapshot=True)

    def delete_all(self):
        self.delete_all_ec2()
        self.delete_all_rds()

    def setup_method(self, method):
        self.delete_all()

    def _test_constructor(self):
        # happy path
        id1 = "test1"
        ec2_id1 = self.launch_ec2(id1)
        rds_id1 = self.launch_rds(id1)

        id2 = "test2"
        ec2_id2 = self.launch_ec2(id2)
        rds_id2 = self.launch_rds(id2)

        server = Server.get_server(id1, self.ec2_client, self.rds_client)
        assert server.ec2_inst.id == ec2_id1
        assert server.rds_inst.id == rds_id1

        server_mapper = Server.batch_get_server(
            ids=[id1, id2], ec2_client=self.ec2_client, rds_client=self.rds_client
        )
        for (
            id,
            ec2_id,
            rds_id,
        ) in [
            (id1, ec2_id1, rds_id1),
            (id2, ec2_id2, rds_id2),
        ]:
            assert server_mapper[id].ec2_inst.id == ec2_id
            assert server_mapper[id].rds_inst.id == rds_id

        # duplicate
        self.launch_ec2(id1)
        with pytest.raises(ServerNotUniqueError):
            Server.batch_get_server(
                ids=[
                    id1,
                ],
                ec2_client=self.ec2_client,
                rds_client=self.rds_client,
            )

        # not exists
        server_mapper = Server.batch_get_server(
            ids=[
                "test3",
            ],
            ec2_client=self.ec2_client,
            rds_client=self.rds_client,
        )
        assert server_mapper["test3"].is_exists() is False

    def _test_status(self):
        id = "sbx-blue"
        ec2_id = self.launch_ec2(id)
        rds_id = self.launch_rds(id)
        server = Server.get_server(id, self.ec2_client, self.rds_client)
        assert server.env_name == "sbx"
        assert server.server_name == "blue"

        assert server.is_exists() is True
        assert server.is_running() is True
        assert server.is_ec2_exists() is True
        assert server.is_ec2_running() is True
        assert server.is_rds_exists() is True
        assert server.is_rds_running() is True

        _ = server.ensure_ec2_exists()
        with pytest.raises(ServerAlreadyExistsError):
            _ = server.ensure_ec2_not_exists()
        _ = server.ensure_rds_exists()
        with pytest.raises(ServerAlreadyExistsError):
            _ = server.ensure_rds_not_exists()
        _ = server.ensure_ec2_is_running()
        with pytest.raises(FailedToStartServerError):
            _ = server.ensure_ec2_is_ready_to_start()
        _ = server.ensure_ec2_is_ready_to_stop()
        _ = server.ensure_rds_is_running()
        with pytest.raises(FailedToStartServerError):
            _ = server.ensure_rds_is_ready_to_start()
        _ = server.ensure_rds_is_ready_to_stop()

        _ = server.server_lifecycle
        _ = server.wow_status
        _ = server.wow_status_measure_time

        self.ec2_client.stop_instances(InstanceIds=[server.ec2_inst.id])
        server.refresh(ec2_client=self.ec2_client, rds_client=self.rds_client)

        assert server.is_exists() is True
        assert server.is_running() is False
        assert server.is_ec2_exists() is True
        assert server.is_ec2_running() is False
        assert server.is_rds_exists() is True
        assert server.is_rds_running() is True

        _ = server.ensure_ec2_exists()
        with pytest.raises(ServerAlreadyExistsError):
            _ = server.ensure_ec2_not_exists()
        _ = server.ensure_rds_exists()
        with pytest.raises(ServerAlreadyExistsError):
            _ = server.ensure_rds_not_exists()
        with pytest.raises(ServerStatusError):
            _ = server.ensure_ec2_is_running()
        _ = server.ensure_ec2_is_ready_to_start()
        with pytest.raises(FailedToStopServerError):
            _ = server.ensure_ec2_is_ready_to_stop()
        _ = server.ensure_rds_is_running()
        with pytest.raises(FailedToStartServerError):
            _ = server.ensure_rds_is_ready_to_start()
        _ = server.ensure_rds_is_ready_to_stop()

        self.rds_client.stop_db_instance(DBInstanceIdentifier=server.rds_inst.id)
        server.refresh(ec2_client=self.ec2_client, rds_client=self.rds_client)

        assert server.is_exists() is True
        assert server.is_running() is False
        assert server.is_ec2_exists() is True
        assert server.is_ec2_running() is False
        assert server.is_rds_exists() is True
        assert server.is_rds_running() is False

        _ = server.ensure_ec2_exists()
        with pytest.raises(ServerAlreadyExistsError):
            _ = server.ensure_ec2_not_exists()
        _ = server.ensure_rds_exists()
        with pytest.raises(ServerAlreadyExistsError):
            _ = server.ensure_rds_not_exists()
        with pytest.raises(ServerStatusError):
            _ = server.ensure_ec2_is_running()
        _ = server.ensure_ec2_is_ready_to_start()
        with pytest.raises(FailedToStopServerError):
            _ = server.ensure_ec2_is_ready_to_stop()
        with pytest.raises(ServerStatusError):
            _ = server.ensure_rds_is_running()
        _ = server.ensure_rds_is_ready_to_start()
        with pytest.raises(FailedToStopServerError):
            _ = server.ensure_rds_is_ready_to_stop()

        self.ec2_client.terminate_instances(InstanceIds=[server.ec2_inst.id])
        server.refresh(ec2_client=self.ec2_client, rds_client=self.rds_client)

        assert server.is_exists() is False
        assert server.is_running() is False
        assert server.is_ec2_exists() is False
        assert server.is_ec2_running() is False
        assert server.is_rds_exists() is True
        assert server.is_rds_running() is False

        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_ec2_exists()
        _ = server.ensure_ec2_not_exists()
        _ = server.ensure_rds_exists()
        with pytest.raises(ServerAlreadyExistsError):
            _ = server.ensure_rds_not_exists()
        with pytest.raises(ServerStatusError):
            _ = server.ensure_ec2_is_running()
        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_ec2_is_ready_to_start()
        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_ec2_is_ready_to_stop()
        with pytest.raises(ServerStatusError):
            _ = server.ensure_rds_is_running()
        _ = server.ensure_rds_is_ready_to_start()
        with pytest.raises(FailedToStopServerError):
            _ = server.ensure_rds_is_ready_to_stop()

        self.rds_client.delete_db_instance(DBInstanceIdentifier=server.rds_inst.id)
        server.refresh(ec2_client=self.ec2_client, rds_client=self.rds_client)

        assert server.is_exists() is False
        assert server.is_running() is False
        assert server.is_ec2_exists() is False
        assert server.is_ec2_running() is False
        assert server.is_rds_exists() is False
        assert server.is_rds_running() is False

        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_ec2_exists()
        _ = server.ensure_ec2_not_exists()
        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_rds_exists()
        _ = server.ensure_rds_not_exists()
        with pytest.raises(ServerStatusError):
            _ = server.ensure_ec2_is_running()
        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_ec2_is_ready_to_start()
        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_ec2_is_ready_to_stop()
        with pytest.raises(ServerStatusError):
            _ = server.ensure_rds_is_running()
        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_rds_is_ready_to_start()
        with pytest.raises(ServerNotFoundError):
            _ = server.ensure_rds_is_ready_to_stop()

    def test(self):
        self._test_constructor()
        self._test_status()


if __name__ == "__main__":
    from acore_server_metadata.tests import run_cov_test

    run_cov_test(__file__, "acore_server_metadata.server", preview=False)
