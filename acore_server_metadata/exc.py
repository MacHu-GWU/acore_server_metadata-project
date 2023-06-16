# -*- coding: utf-8 -*-


class ServerNotFoundError(Exception):
    """
    Raises when a :class:`~acore_server_metadata.server.Server` is not found.
    """
    pass


class ServerNotUniqueError(Exception):
    """
    Raises when there are multiple  :class:`~acore_server_metadata.server.Server`
    has the same id.
    """
    pass
