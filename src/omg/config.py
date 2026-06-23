"""CLI configuration — the gateway endpoint + auth token.

The transport-only CLI knows only *where* the LUDO **gateway** is and *how* to
authenticate to it. The gateway (euroblaze/ludo-gateway) is the single public
door in front of the broker; omg never reaches the agent or NATS directly, holds
no Odoo credentials, and imports no engine code.

Resolution order (per field): environment variable, else default.
  LUDO_API_URL    base URL of the gateway (Contract A); root holds /healthz,
                  the rest is under /api/v1
  LUDO_API_TOKEN  bearer token for that deployment (anon is 404 on tenant data)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# House rule: address deployments by the loopback alias, never localhost.
# Default = the gateway's public edge port.
DEFAULT_API_URL = "http://10.0.99.1:8080"


@dataclass(frozen=True)
class Config:
    """Resolved CLI config — endpoint + optional bearer token."""

    api_url: str
    token: str | None


def load_config() -> Config:
    """Resolve config from the environment, falling back to defaults."""
    return Config(
        api_url=os.environ.get("LUDO_API_URL", "").strip() or DEFAULT_API_URL,
        token=os.environ.get("LUDO_API_TOKEN", "").strip() or None,
    )
