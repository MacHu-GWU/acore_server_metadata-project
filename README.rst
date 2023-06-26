
.. .. image:: https://readthedocs.org/projects/acore-server-metadata/badge/?version=latest
    :target: https://acore-server-metadata.readthedocs.io/en/latest/
    :alt: Documentation Status

.. image:: https://github.com/MacHu-GWU/acore_server_metadata-project/workflows/CI/badge.svg
    :target: https://github.com/MacHu-GWU/acore_server_metadata-project/actions?query=workflow:CI

.. image:: https://codecov.io/gh/MacHu-GWU/acore_server_metadata-project/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/MacHu-GWU/acore_server_metadata-project

.. image:: https://img.shields.io/pypi/v/acore-server-metadata.svg
    :target: https://pypi.python.org/pypi/acore-server-metadata

.. image:: https://img.shields.io/pypi/l/acore-server-metadata.svg
    :target: https://pypi.python.org/pypi/acore-server-metadata

.. image:: https://img.shields.io/pypi/pyversions/acore-server-metadata.svg
    :target: https://pypi.python.org/pypi/acore-server-metadata

.. image:: https://img.shields.io/badge/Release_History!--None.svg?style=social
    :target: https://github.com/MacHu-GWU/acore_server_metadata-project/blob/main/release-history.rst

.. image:: https://img.shields.io/badge/STAR_Me_on_GitHub!--None.svg?style=social
    :target: https://github.com/MacHu-GWU/acore_server_metadata-project

------

.. .. image:: https://img.shields.io/badge/Link-Document-blue.svg
    :target: https://acore-server-metadata.readthedocs.io/en/latest/

.. .. image:: https://img.shields.io/badge/Link-API-blue.svg
    :target: https://acore-server-metadata.readthedocs.io/en/latest/py-modindex.html

.. image:: https://img.shields.io/badge/Link-Install-blue.svg
    :target: `install`_

.. image:: https://img.shields.io/badge/Link-GitHub-blue.svg
    :target: https://github.com/MacHu-GWU/acore_server_metadata-project

.. image:: https://img.shields.io/badge/Link-Submit_Issue-blue.svg
    :target: https://github.com/MacHu-GWU/acore_server_metadata-project/issues

.. image:: https://img.shields.io/badge/Link-Request_Feature-blue.svg
    :target: https://github.com/MacHu-GWU/acore_server_metadata-project/issues

.. image:: https://img.shields.io/badge/Link-Download-blue.svg
    :target: https://pypi.org/pypi/acore-server-metadata#files


Welcome to ``acore_server_metadata`` Documentation
==============================================================================
**背景**

`AzerothCore <https://www.azerothcore.org/>`_ (acore) 是一个开源的魔兽世界模拟器, 其代码质量以及文档是目前 (2023 年) 我看来所有的开源魔兽世界模拟器中最好的. 根据魔兽世界官服服务器的架构, 每一个 realm (大区下的某个服务器, 例如国服著名的山丘之王, 洛萨等) 一般都对应着一个单体虚拟机和一个单体数据库. 一个大区下有很多这种服务器, 而在生产环境和测试开发环境下又分别有很多这种服务器. 所以我需要开发一个工具对于这些服务器进行管理, 健康检查等.

我假设游戏服务器虚拟机和数据库都是在 AWS 上用 EC2 和 RDS 部署的. 所以这个项目只能用于 AWS 环境下的服务器管理.

**关于本项目**

本项目是一个简单的 Python 包, 提供了对一个 realm 服务器的抽象.

**基础用例, 获取服务器状态**

.. code-block:: python

    # 获取服务器的状态
    >>> import boto3
    >>> from acore_server_metadata.api import Server
    >>> server_id = "prod"
    >>> server = Server.get_server(server_id, ec2_client, rds_client)
    >>> server
    Server(
        id='prod-1',
        ec2_inst=Ec2Instance(
            id='i-1a2b3c4d',
            status='running',
            ...
            tags={'wserver:server_id': 'prod'},
            data=...
        ),
        rds_inst=RDSDBInstance(
            id='db-inst-1',
            status='available',
            tags={'wserver:server_id': 'prod'},
            data=...
        ),
    )

    # 检查服务器的状态
    >>> server.is_exists()
    >>> server.is_running()
    >>> server.is_ec2_exists()
    >>> server.is_ec2_running()
    >>> server.is_rds_exists()
    >>> server.is_rds_running()

    # 重新获取服务器的状态
    >>> server.refresh()

    # 批量获取服务器的状态, 进行了一些优化, 以减少 API 调用次数
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

**对服务器进行操作**

.. code-block:: python

    # 创建新的 EC2
    >>> server.run_ec2(ec2_client, ami_id, instance_type, ...)
    # 创建新的 DB Instance
    >>> server.run_rds(rds_client, db_snapshot_identifier, db_instance_class, ...)
    # 启动 EC2
    >>> server.start_ec2(ec2_client)
    # 启动 RDS
    >>> server.start_rds(rds_client)
    # 停止 EC2
    >>> server.stop_ec2(ec2_client)
    # 停止 RDS
    >>> server.stop_rds(rds_client)
    # 删除 EC2
    >>> server.delete_ec2(ec2_client)
    # 删除 RDS
    >>> server.delete_rds(rds_client)
    # 更新 DB 的 master password
    >>> server.update_db_master_password(rds_client, master_password)
    # 关联 EIP 地址
    >>> server.associate_eip_address(...)
    # 创建数据库备份
    >>> server.create_db_snapshot(...)
    # 清理数据库备份
    >>> server.cleanup_db_snapshot(...)


.. _install:

Install
------------------------------------------------------------------------------

``acore_server_metadata`` is released on PyPI, so all you need is to:

.. code-block:: console

    $ pip install acore-server-metadata

To upgrade to latest version:

.. code-block:: console

    $ pip install --upgrade acore-server-metadata
