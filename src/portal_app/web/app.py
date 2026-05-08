from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template

from portal_app.config import PortalConfig, load_config
from portal_app.docker_client import get_container_states
from portal_app.health import HealthChecker


def create_app(config: PortalConfig | None = None) -> Flask:
    cfg = config or load_config()

    package_root = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(package_root / "templates"),
        static_folder=str(package_root / "static"),
    )
    app.config["PORTAL"] = cfg
    app.config["HEALTH"] = HealthChecker(
        timeout_seconds=cfg.health_timeout_seconds,
        cache_seconds=cfg.health_cache_seconds,
    )

    @app.route("/")
    def index():
        tiles = _build_tiles(cfg, app.config["HEALTH"])
        return render_template("index.html", host=cfg.external_host, tiles=tiles)

    @app.route("/api/status")
    def api_status():
        tiles = _build_tiles(cfg, app.config["HEALTH"])
        return jsonify({
            "host": cfg.external_host,
            "tiles": [
                {
                    "name": t["app"].name,
                    "slug": t["app"].slug,
                    "url": t["url"],
                    "status": t["status"],
                    "container": t["container_status"],
                    "latency_ms": t["latency_ms"],
                }
                for t in tiles
            ],
        })

    @app.route("/healthz")
    def healthz():
        return {"ok": True}, 200

    return app


def _build_tiles(cfg: PortalConfig, checker: HealthChecker) -> list[dict]:
    apps = list(cfg.apps)
    container_states = get_container_states([a.container for a in apps])
    health = checker.check_all(apps)

    tiles: list[dict] = []
    for app_tile in apps:
        c_state = container_states.get(app_tile.container)
        h_result = health.get(app_tile.slug)

        if h_result and h_result.reachable:
            status = "up"
        elif c_state and c_state.running:
            # Container running but health check failed
            status = "degraded"
        elif c_state and c_state.exists:
            status = "down"
        elif c_state and not c_state.exists and c_state.status == "missing":
            status = "missing"
        else:
            status = "unknown"

        tiles.append({
            "app": app_tile,
            "url": app_tile.external_url(cfg.external_host),
            "status": status,
            "container_status": c_state.status if c_state else "unknown",
            "latency_ms": h_result.latency_ms if h_result else None,
            "error": h_result.error if h_result else None,
        })
    return tiles
