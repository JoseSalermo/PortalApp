from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AppTile:
    name: str
    description: str
    icon: str
    container: str
    external_port: int
    internal_url: str
    health_path: str = "/"
    healthy_status_codes: tuple[int, ...] = (200, 201, 202, 203, 204, 301, 302)

    @property
    def slug(self) -> str:
        return self.container

    def external_url(self, host: str) -> str:
        return f"{host.rstrip('/')}:{self.external_port}"

    def health_url(self) -> str:
        return f"{self.internal_url.rstrip('/')}{self.health_path}"


@dataclass(frozen=True)
class PortalConfig:
    external_host: str
    health_timeout_seconds: float
    health_cache_seconds: float
    apps: tuple[AppTile, ...] = field(default_factory=tuple)


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "apps.yaml"


def load_config(path: Path | None = None) -> PortalConfig:
    config_path = Path(path or os.environ.get("PORTAL_CONFIG", DEFAULT_CONFIG_PATH))
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    external_host = os.environ.get("PORTAL_EXTERNAL_HOST") or raw.get(
        "external_host", "http://localhost"
    )

    apps = tuple(_parse_app(item) for item in raw.get("apps", []))

    return PortalConfig(
        external_host=external_host,
        health_timeout_seconds=float(raw.get("health_timeout_seconds", 3)),
        health_cache_seconds=float(raw.get("health_cache_seconds", 15)),
        apps=apps,
    )


def _parse_app(item: dict) -> AppTile:
    healthy = item.get("healthy_status_codes")
    if healthy is None:
        healthy_codes: tuple[int, ...] = (200, 201, 202, 203, 204, 301, 302)
    else:
        healthy_codes = tuple(int(c) for c in healthy)

    return AppTile(
        name=item["name"],
        description=item.get("description", ""),
        icon=item.get("icon", ""),
        container=item["container"],
        external_port=int(item["external_port"]),
        internal_url=item["internal_url"],
        health_path=item.get("health_path", "/"),
        healthy_status_codes=healthy_codes,
    )
