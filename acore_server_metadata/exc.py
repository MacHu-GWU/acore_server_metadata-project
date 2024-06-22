# -*- coding: utf-8 -*-


class ServerNotUniqueError(Exception):
    """
    Raises when there are multiple  :class:`~acore_server_metadata.server.Server`
    has the same id.
    """

    pass


class ServerStatusError(Exception):
    """
    Raises when the status of the EC2 or RDS or server doesn't meet the expectation
    """


class ServerNotFoundError(ServerStatusError):
    """
    Raises when a :class:`~acore_server_metadata.server.Server` is not found.
    """


class ServerAlreadyExistsError(ServerStatusError):
    """
    Raises when try to launch a new EC2 or DB instance when there is already
    a existing one.
    """


class FailedToStartServerError(ServerStatusError):
    """
    Raises when the current EC2 and RDS state is not ready for start.
    (It has to exist first).
    """


class FailedToStopServerError(ServerStatusError):
    """
    Raises when the current EC2 and RDS state is not ready for stop.
    (It has to exist first).
    """
