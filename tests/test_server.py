# -*- coding: utf-8 -*-

import typing as T
import moto
import time
import pytest

from acore_server_metadata.tests.mock_aws import BaseMockTest
from acore_server_metadata.settings import settings
from acore_server_metadata.server import ServerNotUniqueError, Server


class TestServer(BaseMockTest):
    mock_list = [
        moto.mock_sts,
        moto.mock_ec2,
        moto.mock_rds,
    ]

    @classmethod
    def start_instance(cls, id: str) -> T.Tuple[str, str]:
        """
        return ec2 id and rds id
        """
        image_id = cls.bsm.ec2_client.describe_images()["Images"][0]["ImageId"]

        ec2_id = cls.bsm.ec2_client.run_instances(
            MinCount=1,
            MaxCount=1,
            ImageId=image_id,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": settings.ID_TAG_KEY, "Value": id},
                    ],
                },
            ],
        )["Instances"][0]["InstanceId"]

        rds_id = cls.bsm.rds_client.create_db_instance(
            DBInstanceIdentifier="db-inst-1",
            DBInstanceClass="db.t2.micro",
            Engine="mysql",
            Tags=[
                {"Key": settings.ID_TAG_KEY, "Value": id},
            ],
        )["DBInstance"]["DBInstanceIdentifier"]

        return ec2_id, rds_id

    def _test(self):
        ec2_id, rds_id = self.start_instance(id="test")

        # server exists
        server = Server.get_server(
            id="test",
            ec2_client=self.bsm.ec2_client,
            rds_client=self.bsm.rds_client,
        )
        assert server.is_exists() is True
        assert server.is_running() is True
        assert server.is_ec2_exists() is True
        assert server.is_ec2_running() is True
        assert server.is_rds_exists() is True
        assert server.is_rds_running() is True

        server.ec2_inst.stop_instance(self.bsm.ec2_client)
        server.rds_inst.stop_db_instance(self.bsm.rds_client)
        server.refresh(ec2_client=self.bsm.ec2_client, rds_client=self.bsm.rds_client)
        assert server.is_exists() is True
        assert server.is_running() is False
        assert server.is_ec2_exists() is True
        assert server.is_ec2_running() is False
        assert server.is_rds_exists() is True
        assert server.is_rds_running() is False

        # server not exists
        server = Server.get_server(
            id="dev",
            ec2_client=self.bsm.ec2_client,
            rds_client=self.bsm.rds_client,
        )
        assert server is None

        server = Server(id="dev")
        server.refresh(ec2_client=self.bsm.ec2_client, rds_client=self.bsm.rds_client)
        assert server.is_exists() is False
        assert server.is_running() is False
        assert server.is_ec2_exists() is False
        assert server.is_ec2_running() is False
        assert server.is_rds_exists() is False
        assert server.is_rds_running() is False

        # start another server with the same tag, then we got collision issue
        self.start_instance(id="test")
        with pytest.raises(ServerNotUniqueError):
            server = Server.get_server(
                id="test",
                ec2_client=self.bsm.ec2_client,
                rds_client=self.bsm.rds_client,
            )

    def _test_batch_get_server(self):
        # some server exists, some not
        self.start_instance(id="prod-1")
        server_mapper = Server.batch_get_server(
            ids=["prod-1", "prod-2"],
            ec2_client=self.bsm.ec2_client,
            rds_client=self.bsm.rds_client,
        )
        server1 = server_mapper["prod-1"]
        assert server1.is_exists() is True
        assert server1.is_running() is True
        assert server1.is_ec2_exists() is True
        assert server1.is_ec2_running() is True
        assert server1.is_rds_exists() is True
        assert server1.is_rds_running() is True
        assert server_mapper["prod-2"] is None

        # start another server with the same tag, then we got collision issue
        self.start_instance(id="prod-1")
        with pytest.raises(ServerNotUniqueError):
            Server.batch_get_server(
                ids=["prod-1", "prod-2"],
                ec2_client=self.bsm.ec2_client,
                rds_client=self.bsm.rds_client,
            )

    def _test_operations(self):
        server = Server(id="test-operations")
        self.start_instance(server.id)
        server.refresh(ec2_client=self.bsm.ec2_client, rds_client=self.bsm.rds_client)

        server.create_db_snapshot(rds_client=self.bsm.rds_client)
        time.sleep(1)
        server.create_db_snapshot(rds_client=self.bsm.rds_client)
        time.sleep(1)
        server.create_db_snapshot(rds_client=self.bsm.rds_client)

        server.cleanup_db_snapshot(rds_client=self.bsm.rds_client, keep_n=1, keep_days=0)

    def test(self):
        self._test()
        self._test_batch_get_server()
        self._test_operations()


if __name__ == "__main__":
    from acore_server_metadata.tests import run_cov_test

    run_cov_test(__file__, "acore_server_metadata.server", preview=False)
