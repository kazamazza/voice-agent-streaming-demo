from __future__ import annotations

from enum import StrEnum


class Route(StrEnum):
    SUPPORT = "SUPPORT"
    SALES = "SALES"
    BILLING = "BILLING"
    HUMAN_AGENT = "HUMAN_AGENT"
    UNKNOWN = "UNKNOWN"


ROUTE_VALUES: set[str] = {r.value for r in Route}
