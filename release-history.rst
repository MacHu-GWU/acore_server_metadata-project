.. _release_history:

Release and Version History
==============================================================================


x.y.z (Backlog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


0.7.1 (2024-06-15)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- Add ``Server.server_lifecycle``, ``Server.wow_status``, ``Server.wow_status_measure_time`` property method.
- Add ``Server.start_server()`` method.
- Add ``allow_reassociation`` parameter to ``Server.associate_eip_address()`` method.

**Minor Improvements**

- Improve documentation.


0.6.2 (2023-06-28)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Miscellaneous**

- upgrade dependencies.
- improve internal implementation.


0.6.1 (2023-06-27)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- add the following public API:
    - ``acore_server_metadata.api.Server.from_ec2_inside``
    - ``acore_server_metadata.api.get_boto_ses_from_ec2_inside``

**Miscellaneous**

- upgrade dependencies.


0.5.2 (2023-06-26)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Minor Improvements**

- ``acore_server_metadata.settings`` module is not in used anymore. It is kept for backward compatibility. Now we use `acore_constants <https://github.com/MacHu-GWU/acore_constants-project>`_ library to define constants.


0.5.1 (2023-06-22)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- Now the ``acore_server_metadata.api.Server.get_server()`` method will always return a ``Server`` object. If the ec2 or rds doesn't not exists, then the ``ec2_inst`` or ``rds_inst`` attribure of the ``Server`` object will be ``None``. This behavior was returning ``None`` before.
- Similarly the ``acore_server_metadata.api.Server.batch_get_server()`` method will always return a ``Server`` object for specific id.

**Minor Improvements**

- add many unit test to cover the server operations API.


0.4.5 (2023-06-21)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Bugfixes**

- fix a bug when "check=True", we didn't use the object representing the latest ec2 or rds metadata.


0.4.4 (2023-06-20)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Minor Improvements**

- ``acore_server_metadata.api.Server.run_rds`` now also copy ``tech:master_password_digest`` tag from snapshot to RDS instance.


0.4.3 (2023-06-19)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Minor Improvements**

- ``acore_server_metadata.api.Server.run_ec2`` and ``acore_server_metadata.api.Server.run_rds`` now receive additional kwargs. The ``allocated_storage`` is no longer mandatory.


0.4.2 (2023-06-19)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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
