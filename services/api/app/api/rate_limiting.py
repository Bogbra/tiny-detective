"""Per-IP rate limiting for public, cost-bearing endpoints (POST /cases/{id}/hint
and POST /cases/generate, both of which call the OpenAI API). This is a
separate concern from domain-level limits like HintPolicy (hint count per
case per player) — those limit how much of a single case a player can see;
this limits how fast any one caller can hit an endpoint at all, regardless
of case or player, which is what actually bounds OpenAI spend once the demo
URL is public.

Keys on X-Forwarded-For rather than the raw socket peer address: behind
Cloud Run's proxy layer, request.client.host reflects Cloud Run's own
internal hop, not the real caller — every request would look like the same
source, either never tripping the limit or (worse) rate-limiting every real
user as if they were one.

**Which XFF entry is trustworthy is not "the first one."** X-Forwarded-For is
a comma-separated list a client can pre-populate with anything before it
ever reaches Cloud Run; Cloud Run then *appends* the real connecting IP as
one more entry. Reading the first entry (the original implementation here)
reads exactly the part an attacker controls — sending a fresh, fabricated
first entry on every request bypasses the per-IP limit entirely by rotating
"fake IPs" that were never actually used to connect. The trustworthy entry
is the one appended by infrastructure we actually trust, counted from the
*end* of the list: with exactly one trusted hop (Cloud Run itself, the
default), that's the last entry. TRUSTED_PROXY_HOPS (env var, default 1)
makes this configurable — set to 2 if an additional trusted proxy (e.g. an
external load balancer) is ever placed in front of Cloud Run and also
appends its own hop, so the real client is then the second-to-last entry.

Falls back to the raw peer address when the header is absent (local dev,
tests).
"""

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

DEFAULT_TRUSTED_PROXY_HOPS = 1
TRUSTED_PROXY_HOPS_ENV_VAR = "TRUSTED_PROXY_HOPS"


def _trusted_proxy_hops() -> int:
    raw = os.environ.get(TRUSTED_PROXY_HOPS_ENV_VAR)
    if raw is None:
        return DEFAULT_TRUSTED_PROXY_HOPS
    try:
        hops = int(raw)
    except ValueError:
        return DEFAULT_TRUSTED_PROXY_HOPS
    return hops if hops >= 1 else DEFAULT_TRUSTED_PROXY_HOPS


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
        if hops:
            # The Nth-from-the-end entry, where N = trusted proxy hops —
            # never the first entry, which is attacker-controlled. Clamped
            # to the earliest available entry if the header has fewer
            # entries than expected trusted hops, rather than raising.
            index = -min(_trusted_proxy_hops(), len(hops))
            return hops[index]
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip)
