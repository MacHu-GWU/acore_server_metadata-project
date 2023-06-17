.. _release_history:

Release and Version History
==============================================================================


x.y.z (Backlog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


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
