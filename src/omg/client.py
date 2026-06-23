"""Transport client — talks to the LUDO **gateway** over Contract A (REST + SSE).

The gateway (euroblaze/ludo-gateway) is the single public door in front of the
broker. This client depends only on public HTTP + the vendored contract schemas
(contracts/). No engine import, no NATS, no Odoo credentials. Write commands
(approve / job submit) land in P4 once the gated broker write path is cleared.
"""
# Every method returns parsed JSON (Any); the declared return types document the
# shape. Suppress no-any-return file-wide rather than cast at every call site.
# mypy: disable-error-code="no-any-return"

from __future__ import annotations

import json
from collections.abc import Iterator
from types import TracebackType
from typing import Any

import httpx

from omg.config import Config


class LudoClient:
    """Thin HTTP client over the gateway's public API."""

    def __init__(self, config: Config, *, timeout: float = 30.0) -> None:
        headers = {"Accept": "application/json"}
        if config.token:
            headers["Authorization"] = f"Bearer {config.token}"
        self._http = httpx.Client(base_url=config.api_url, headers=headers, timeout=timeout)

    # ── read surface (Contract A) ──────────────────────────────────────
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        r = self._http.get(path, params=clean or None)
        r.raise_for_status()
        return r.json()

    def healthz(self) -> dict[str, Any]:
        """Gateway liveness — ``{"ok": true}``."""
        return self._get("/healthz")

    def system_status(self) -> dict[str, Any]:
        """Gateway environment — ``{app_env, broker_mode}``."""
        return self._get("/system/status")

    def list_migrations(self) -> dict[str, Any]:
        """The caller's migrations — ``{"items": [...]}`` (tenant-scoped)."""
        return self._get("/api/v1/migrations")

    def get_migration(self, migration_id: str) -> dict[str, Any]:
        """One migration's detail (404 if out of scope / not found)."""
        return self._get(f"/api/v1/migrations/{migration_id}")

    def stream_events(self, migration_id: str, last_event_id: int | None = None) -> Iterator[tuple[int, str, Any]]:
        """Stream the migration's resumable Contract B SSE.

        Yields ``(seq, type, payload)`` per event; resumes from ``last_event_id``
        (the stream sequence) when given. Ends on ``session_end``.
        """
        headers = {"Accept": "text/event-stream"}
        if last_event_id is not None:
            headers["Last-Event-ID"] = str(last_event_id)
        with self._http.stream(
            "GET", f"/api/v1/migrations/{migration_id}/events", headers=headers, timeout=None
        ) as resp:
            if resp.is_error:
                # Streaming body isn't read yet; load it so raise_for_status /
                # .text work instead of throwing ResponseNotRead.
                resp.read()
                resp.raise_for_status()
            seq = 0
            etype = "message"
            data_buf: list[str] = []
            for line in resp.iter_lines():
                if line == "":  # frame boundary
                    if data_buf:
                        raw = "\n".join(data_buf)
                        try:
                            payload: Any = json.loads(raw)
                        except json.JSONDecodeError:
                            payload = raw
                        yield (seq, etype, payload)
                    etype, data_buf = "message", []
                    continue
                if line.startswith("id:"):
                    val = line[3:].strip()
                    seq = int(val) if val.isdigit() else seq
                elif line.startswith("event:"):
                    etype = line[6:].strip()
                elif line.startswith("data:"):
                    data_buf.append(line[5:].lstrip())

    # ── lifecycle ──────────────────────────────────────────────────────
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> LudoClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
