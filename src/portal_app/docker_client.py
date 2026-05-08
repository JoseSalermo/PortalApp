from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContainerState:
    exists: bool
    running: bool
    status: str  # "running", "exited", "missing", "unknown"


_MISSING = ContainerState(exists=False, running=False, status="missing")
_UNKNOWN = ContainerState(exists=False, running=False, status="unknown")


def get_container_states(names: list[str]) -> dict[str, ContainerState]:
    """Look up each container by name. Falls back to 'unknown' if the docker
    socket is not reachable (e.g. running outside docker without /var/run/docker.sock).
    """
    try:
        import docker
        from docker.errors import DockerException, NotFound
    except ImportError:
        logger.warning("docker SDK not installed; container state unavailable")
        return {name: _UNKNOWN for name in names}

    try:
        client = docker.from_env()
    except DockerException as exc:
        logger.warning("docker socket unreachable: %s", exc)
        return {name: _UNKNOWN for name in names}

    out: dict[str, ContainerState] = {}
    for name in names:
        try:
            container = client.containers.get(name)
        except NotFound:
            out[name] = _MISSING
            continue
        except DockerException as exc:
            logger.warning("docker error for %s: %s", name, exc)
            out[name] = _UNKNOWN
            continue

        status = container.status  # "running", "exited", "paused", "created", ...
        out[name] = ContainerState(
            exists=True,
            running=(status == "running"),
            status=status,
        )
    return out
