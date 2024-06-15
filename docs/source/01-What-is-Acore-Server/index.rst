What is acore Server
==============================================================================


An acore Server is an EC2 and RDS
------------------------------------------------------------------------------
Acore Server (AS) 指的是一个能让人 Log in 的魔兽世界游戏服务器. 它包含一台 EC2 来运行游戏服务器, 和一台 RDS 数据库.


One RDS Instance can Have multiple Databases
------------------------------------------------------------------------------
一个 RDS Instance 是一个安装了 MySQL 数据库的虚拟机. 一个 MySQL 数据库中是可以创建很多个 database 的. 根据魔兽世界服务器的设计, 一般会有 auth, world, player 三个数据库. 这三个数据库既可以放在同一个 DB Instance 上, 也可以放在不同的 DB Instance 上.


Server and Realm in Retail
------------------------------------------------------------------------------
在官方服务器上, 一个大区 (比如美服) 会有很多组服务器. 这些服务器在数据库中会被注册为不同的 Realm. 所以实际上我们这个项目中的 AS 对应的是一个 Realm 的概念.


.. _why-we-dont-let-server-share-databases:

Why We Don't Let Server Share Databases
------------------------------------------------------------------------------
在官方服务器上, 一个大区 (比如美服) 会有很多组服务器. 这些服务器在数据库中会被注册为不同的 realm. 在生产实践中, 一般是 auth, world, player 三个数据库分别部署, 分别 scale. 并且每个 Realm 都要有自己单独的 player 的数据库.

.. note::

    这里的数据库不是 DB Instance, 而是 database 的概念.

但是在我们自己开私服的情况下, 我们为了节约成本一般会将这三个数据库都放在同一个 Instance 上. 而又因为我们没有说开多个 Realm 的需求, 所以我们就用一个 DB Instance 来为一个 Realm 提供服务了.


.. _environment-name-and-server-name:

Environment Name and Server Name
------------------------------------------------------------------------------
我们参照软件工程中的环境的概念, 我们也有多个开发环境, 包括 sbx, tst, prd. 在一个环境中, 每个 AS 都有一个唯一的名字, 例如 blue, green, white, black, yellow, orange 等.

.. important::

    所以在全局看来, 一个 AS 的全局唯一 ID 是由 ``${env_name}-${as_name}`` 组成的. 例如 ``sbx-blue``, ``sbx-green``, ``prd-white``, ``prd-black``.

    这个全局的 ID 也叫做 Server Name (``server_name``)


.. _blue-green-deployment:

Blue Green Deployment
------------------------------------------------------------------------------
在我们升级游戏服务器核心的版本, 升级数据库, 或者更新功能时, 我们不会在正在运行着的 AS 上进行修改. 我们会创建一个新的 AS 作为开发, 开发完成后关闭旧的 AS, 并对旧的 AS 进行备份. 如果新的 AS 出现问题, 我们可以快速切换回旧的 AS.

.. caution::

    如果你的升级包括了大量数据库改动, 那么这种回滚就会造成数据回档. 因为新的数据库已经被写入了新的数据, 而你无法将新的数据库同步到旧的数据库上 (因为不兼容).

我们一般把 blue/green 分为一组, white/black 分为一组, yello/orange 分为一组. 而 red 作为一个单独的, 用于测试的 sandbox.
