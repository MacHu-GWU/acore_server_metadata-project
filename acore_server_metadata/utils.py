# -*- coding: utf-8 -*-

from datetime import datetime, timezone

def get_utc_now() -> datetime:
    return datetime.utcnow().replace(tzinfo=timezone.utc)
