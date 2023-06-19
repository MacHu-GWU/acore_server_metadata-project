.. _release_history:

Release and Version History
==============================================================================


x.y.z (Backlog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


0.4.2 (2023-06-19)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

- ``acore_server_metadata.api.Server.associate_eip_address`` now returns API response or None
- ``acore_server_metadata.api.Server.update_db_master_password`` now returns API response or None
- ``acore_server_metadata.api.Server.cleanup_db_snapshot`` now returns API response or None
- add ``acore_server_metadata.api.Server.create_ec2``, it is a alias of ``run_ec2``
- add ``acore_server_metadata.api.Server.create_rds``, it is a alias of ``run_rds``


0.4.1 (2023-06-19)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- add the following public API:
    - ``acore_server_metadata.api.Server.start_ec2``
    - ``acore_server_metadata.api.Server.start_rds``
    - ``acore_server_metadata.api.Server.stop_ec2``
    - ``acore_server_metadata.api.Server.stop_rds``
    - ``acore_server_metadata.api.Server.delete_ec2``
    - ``acore_server_metadata.api.Server.delete_rds``


0.3.1 (2023-06-19)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- add ``acore_server_metadata.api.Server.update_db_master_password`` to update the master password of RDS DB instance.


0.2.2 (2023-06-17)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Bugfixes**

- Fix a bug that ``Server.get_ec2`` and ``Server.get_rds`` methods returns terminated ec2 and deleted rds instances. They should be considered as "not exists"


0.2.1 (2023-06-16)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- add ``acore_server_metadata.api.Server.run_ec2`` and ``acore_server_metadata.api.Server.run_rds`` method to launch a new EC2 instance or RDS db instance.
- add ``acore_server_metadata.api.Server.associate_eip_address`` to associate eip address to EC2 instance.
- add ``acore_server_metadata.api.Server.create_db_snapshot`` to create a manual db snapshot for RDS DB instance.
- add ``acore_server_metadata.api.Server.cleanup_db_snapshot`` to clean up old db snapshots for RDS DB instance.


0.1.1 (2023-06-15)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- First release
- Add the following public API:
    - ``acore_server_metadata.api.exc``
    - ``acore_server_metadata.api.settings``
    - ``acore_server_metadata.api.Server``
