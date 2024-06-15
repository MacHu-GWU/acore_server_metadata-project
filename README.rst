
.. image:: https://readthedocs.org/projects/acore-server-metadata/badge/?version=latest
    :target: https://acore-server-metadata.readthedocs.io/en/latest/
    :alt: Documentation Status

.. image:: https://github.com/MacHu-GWU/acore_server_metadata-project/actions/workflows/main.yml/badge.svg
    :target: https://github.com/MacHu-GWU/acore_server_metadata-project/actions?query=workflow:CI:CI

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

.. image:: https://img.shields.io/badge/Link-Document-blue.svg
    :target: https://acore-server-metadata.readthedocs.io/en/latest/

.. image:: https://img.shields.io/badge/Link-API-blue.svg
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
.. image:: https://acore-server-metadata.readthedocs.io/en/latest/_static/acore_server_metadata-logo.png
    :target: https://acore-server-metadata.readthedocs.io/en/latest/

**背景**

`AzerothCore <https://www.azerothcore.org/>`_ (acore) 是一个开源的魔兽世界模拟器, 其代码质量以及文档是目前 (2023 年) 我看来所有的开源魔兽世界模拟器中最好的. 根据魔兽世界官服服务器的架构, 每一个 realm (大区下的某个服务器, 例如国服著名的山丘之王, 洛萨等) 一般都对应着一个单体虚拟机和一个单体数据库. 一个大区下有很多这种服务器, 而在生产环境和测试开发环境下又分别有很多这种服务器. 所以我需要开发一个工具对于这些服务器进行管理, 健康检查等.

我假设游戏服务器虚拟机和数据库都是在 AWS 上用 EC2 和 RDS 部署的. 所以这个项目只能用于 AWS 环境下的服务器管理.

**关于本项目**

本项目把一个游戏服务器抽象成了一个 Python 类, 它包含了一个 EC2 实例和一个 RDS 实例的抽象. 通过这个类, 我们可以获取服务器的状态, 启动服务器, 停止服务器, 删除服务器, 创建数据库备份等操作.



.. _install:

Install
------------------------------------------------------------------------------

``acore_server_metadata`` is released on PyPI, so all you need is to:

.. code-block:: console

    $ pip install acore-server-metadata

To upgrade to latest version:

.. code-block:: console

    $ pip install --upgrade acore-server-metadata
