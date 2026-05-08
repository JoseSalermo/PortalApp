from __future__ import annotations

import argparse
import logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="portal-app")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the portal web server")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8888)
    serve.add_argument("--debug", action="store_true")

    sub.add_parser("status", help="Print tile status to stdout")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.command == "serve":
        from portal_app.web.app import create_app

        app = create_app()
        app.run(host=args.host, port=args.port, debug=args.debug)
        return 0

    if args.command == "status":
        from portal_app.config import load_config
        from portal_app.docker_client import get_container_states
        from portal_app.health import HealthChecker

        cfg = load_config()
        checker = HealthChecker(cfg.health_timeout_seconds, cfg.health_cache_seconds)
        states = get_container_states([a.container for a in cfg.apps])
        health = checker.check_all(list(cfg.apps))

        for app_tile in cfg.apps:
            c = states.get(app_tile.container)
            h = health.get(app_tile.slug)
            print(
                f"{app_tile.name:<28}  "
                f"container={c.status if c else 'unknown':<8}  "
                f"http={'OK' if h and h.reachable else 'FAIL':<4}  "
                f"{app_tile.external_url(cfg.external_host)}"
            )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
