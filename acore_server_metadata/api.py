# -*- coding: utf-8 -*-

from . import exc
from .exc import ServerNotUniqueError
from .exc import ServerStatusError
from .exc import ServerNotFoundError
from .exc import ServerAlreadyExistsError
from .exc import FailedToStartServerError
from .exc import FailedToStopServerError
from .settings import settings
from .server.api import Server
from .utils import get_boto_ses_from_ec2_inside
