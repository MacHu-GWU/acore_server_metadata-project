# -*- coding: utf-8 -*-

from boto_session_manager import BotoSesManager
from rich import print as rprint
from acore_server_metadata.api import Server

bsm = BotoSesManager(profile_name="bmt_app_dev_us_east_1")

ami_id = "ami-06da1d328f46b5a49"
instance_type = "t3.medium"
key_name = "sanhe-dev"
subnet_id = "subnet-03612e5c300084748"
db_subnet_group_name = "wserver-ops-dev-db"
ec2_security_group_ids = [
    "sg-04b74660c10be84a3",
    "sg-0b504cd210dab8fed",
    "sg-0c9546f691e07b49d",
]
rds_security_group_ids = ["sg-0b504cd210dab8fed"]
iam_instance_profile_arn = (
    "arn:aws:iam::111122223333:instance-profile/wserver_ops-dev-us-east-1-ec2"
)

db_snapshot_identifier = "wserver-blue-2023-05-07-01-41-00"
db_instance_class = "db.t4g.small"
master_password = "sbx*dummy4test"

server = Server(id="sbx-blue")
server.refresh(ec2_client=bsm.ec2_client, rds_client=bsm.rds_client)

# server.run_ec2(
#     ec2_client=bsm.ec2_client,
#     ami_id=ami_id,
#     instance_type=instance_type,
#     key_name=key_name,
#     subnet_id=subnet_id,
#     security_group_ids=ec2_security_group_ids,
#     iam_instance_profile_arn=iam_instance_profile_arn,
# )

# server.run_rds(
#     rds_client=bsm.rds_client,
#     db_snapshot_identifier=db_snapshot_identifier,
#     db_instance_class=db_instance_class,
#     db_subnet_group_name=db_subnet_group_name,
#     security_group_ids=rds_security_group_ids,
# )

# server.update_db_master_password(
#     rds_client=bsm.rds_client,
#     master_password=master_password,
# )

# server.ec2_inst.stop_instance(bsm.ec2_client)
# server.rds_inst.stop_db_instance(bsm.rds_client)

# server.create_db_snapshot(bsm.rds_client)
# server.cleanup_db_snapshot(bsm.rds_client)
