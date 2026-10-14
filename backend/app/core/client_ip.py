"""Client IP address, trusting X-Forwarded-For only for the configured number of proxies."""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str:
    trusted: int = request.app.state.settings.trusted_proxy_count
    direct = request.client.host if request.client else "unknown"
    if trusted <= 0:
        return direct
    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    # Each trusted proxy appends the address it received the request from; the real client is the
    # entry just before the ones our proxies added. Anything further left can be spoofed.
    if len(hops) >= trusted:
        return hops[-trusted]
    return direct
