# -*- coding: utf-8 -*-

"""
这个模块下实现了对 server 的抽象. 由于 server 的属性和方法过多, 所以我们用 mixin 设计模式
将其分拆到了多个模块中, 然后统一在 :mod:`acore_server_metadata.server.server` 模块中
将其组装起来.
"""
