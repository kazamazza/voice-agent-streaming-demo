from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Header

from voice_demo.container import build_container


_container = None


def get_container():
    global _container
    if _container is None:
        _container = build_container()
    return _container


def get_request_id(x_request_id: Optional[str] = Header(default=None)) -> str:
    return x_request_id or str(uuid.uuid4())


def get_broker():
    return get_container()["broker"]


def get_state_store():
    return get_container()["state_store"]