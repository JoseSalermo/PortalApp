# PortalApp

Homelab portal for QNAP-hosted services. One page, one tile per app, with live up/down status from Docker and HTTP health checks.

## Layout

- `apps.yaml` — source of truth for tiles (name, url, icon, container, health path)
- `src/portal_app/` — Flask app, Docker discovery, health probes
- `src/portal_app/web/static/icons/` — drop PNG/SVG icons here, referenced by name from `apps.yaml`

## Run locally

```bash
python -m pip install -e .
portal-app serve --host 0.0.0.0 --port 8888
```

Open <http://localhost:8888>.

## Run on QNAP

```bash
docker compose up -d --build
```

The compose file mounts `/var/run/docker.sock:ro` so the portal can read container state. The HTTP health checks run from inside the container, so the URLs in `apps.yaml` must be reachable from the homelab network (use container names, not `localhost`).

## Adding an app

1. Drop `myapp.svg` (or `.png`) into `src/portal_app/web/static/icons/`.
2. Add an entry to `apps.yaml`:
   ```yaml
   - name: My App
     description: What it does
     url: http://my-app:8080
     external_url: http://qnap.local:8080
     icon: myapp.svg
     container: my-app
     health_path: /healthz
   ```
3. Restart the portal.
