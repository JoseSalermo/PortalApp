from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock

import requests

from portal_app.config import AppTile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HealthResult:
    reachable: bool
    status_code: int | None
    latency_ms: int | None
    error: str | None


class HealthChecker:
    def __init__(self, timeout_seconds: float, cache_seconds: float) -> None:
        self._timeout = timeout_seconds
        self._cache_ttl = cache_seconds
        self._cache: dict[str, tuple[float, HealthResult]] = {}
        self._lock = Lock()

    def check_all(self, apps: list[AppTile]) -> dict[str, HealthResult]:
        now = time.time()
        to_probe: list[AppTile] = []
        results: dict[str, HealthResult] = {}

        with self._lock:
            for app in apps:
                cached = self._cache.get(app.slug)
                if cached and (now - cached[0]) < self._cache_ttl:
                    results[app.slug] = cached[1]
                else:
                    to_probe.append(app)

        if to_probe:
            with ThreadPoolExecutor(max_workers=min(8, len(to_probe))) as pool:
                fresh = dict(zip(
                    (a.slug for a in to_probe),
                    pool.map(self._probe, to_probe),
                ))

            with self._lock:
                stamp = time.time()
                for slug, result in fresh.items():
                    self._cache[slug] = (stamp, result)
                    results[slug] = result

        return results

    def _probe(self, app: AppTile) -> HealthResult:
        url = app.health_url()
        started = time.monotonic()
        try:
            resp = requests.get(url, timeout=self._timeout, allow_redirects=False)
        except requests.RequestException as exc:
            return HealthResult(
                reachable=False,
                status_code=None,
                latency_ms=None,
                error=str(exc),
            )
        latency_ms = int((time.monotonic() - started) * 1000)
        ok = resp.status_code in app.healthy_status_codes
        return HealthResult(
            reachable=ok,
            status_code=resp.status_code,
            latency_ms=latency_ms,
            error=None if ok else f"unexpected status {resp.status_code}",
        )
