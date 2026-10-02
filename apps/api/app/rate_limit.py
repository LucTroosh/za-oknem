"""In-process sliding-window rate limiter (ADR-017, Master Plan §64-66).

Per-key (client IP) request counter kept in this process's memory with a short
TTL: the IP is used only for limiting and is never written to PostgreSQL or logs.

ponytail: per-process state - with N uvicorn workers the effective limit is N x
limit, and it resets on restart. Shared limiter (Redis) is TASK-15.4's decision;
extending this to the whole API is TASK-14.2.
"""

import ipaddress
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

MAX_KEYS = 10_000  # memory bound: sweep expired keys once exceeded


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._next_sweep = 0.0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def check(self, key: str) -> None:
        """Record one hit for `key`; HTTP 429 (+ Retry-After) if over the limit."""
        now = time.monotonic()
        with self._lock:
            # Expired keys (= stored IPs) are dropped at least once per window, so the
            # in-memory IP data really lives only ~window seconds (ADR-017).
            if now >= self._next_sweep:
                self._sweep(now)
                self._next_sweep = now + self.window
            if key not in self._hits and len(self._hits) >= MAX_KEYS:
                self._sweep(now)
                # All still active: evict oldest down to 90% so the O(N) sweep does not
                # run on every new key under a flood of distinct IPs.
                while len(self._hits) > MAX_KEYS * 0.9:
                    del self._hits[next(iter(self._hits))]
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, int(hits[0] + self.window - now) + 1)
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def refund(self, key: str) -> None:
        """Give back the newest hit of `key` (a request that failed before doing the work)."""
        with self._lock:
            hits = self._hits.get(key)
            if hits:
                hits.pop()

    def _sweep(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or h[-1] <= now - self.window]:
            del self._hits[key]


# 30 writes/min per IP: a legit app writes a handful of times per session (start,
# token refresh, area change); carrier NAT shares IPs, hence not lower.
device_writes = RateLimiter(limit=30, window_seconds=60)


def client_key(request: Request) -> str:
    """Rate-limit key: the client IP, IPv6 collapsed to its /64 (one subscriber owns a whole
    /64, so per-address keys would be free to rotate). Behind Caddy `request.client` is the
    real client only when uvicorn runs with --proxy-headers and FORWARDED_ALLOW_IPS = the
    proxy (ADR-029, TASK-15 production checklist); otherwise everyone shares one bucket."""
    host = request.client.host if request.client else "unknown"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    if isinstance(ip, ipaddress.IPv6Address):
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return host


def limit_device_writes(request: Request) -> None:
    device_writes.check(client_key(request))


# ADR-029: switching polling on for a place costs Open-Meteo budget, and place ids are
# public and enumerable - so new activations are scarce per IP (refreshing an already active
# area is not counted). A person picks a handful of places an hour at most.
place_activations = RateLimiter(limit=10, window_seconds=3600)


def limit_place_activations(request: Request) -> None:
    place_activations.check(client_key(request))


def refund_place_activation(request: Request) -> None:
    place_activations.refund(client_key(request))
