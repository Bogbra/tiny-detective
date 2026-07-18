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

**Instance-count awareness.** slowapi's default storage is an in-memory
dict, counted per running process — with Cloud Run's `--max-instances=3`
(ADR-0006), a caller whose requests land on different instances can see up
to 3x any single `@limiter.limit(...)` value before any one process's
counter trips. `per_instance_limit(intended_per_minute)` divides an
intended cluster-wide-equivalent rate by `RATE_LIMIT_MAX_INSTANCES` (env
var, default 3, matching `--max-instances`) so the configured per-process
limit stays close to the intended total even under worst-case instance
spread — used for POST /players and POST /cases/{id}/solution, the two
endpoints whose only real defense against write-volume abuse IS this
limiter. POST /hint and POST /cases/generate deliberately keep their
existing literal values instead (5/minute, 3/minute) — both already have a
genuinely cluster-wide backstop underneath the per-IP limiter (the domain
HintPolicy's per-case hint cap, and the Firestore-atomic daily generation
quota respectively), so the 3x per-IP gap there is a fairness/burst
concern, not an unbounded-cost one; dividing those down to ~1-2/minute
would make the endpoints borderline unusable for a real single player for
a gap that's already backstopped elsewhere. See ADR-0006's amendment for
the full reasoning.
"""

import math
import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

DEFAULT_TRUSTED_PROXY_HOPS = 1
TRUSTED_PROXY_HOPS_ENV_VAR = "TRUSTED_PROXY_HOPS"

DEFAULT_RATE_LIMIT_MAX_INSTANCES = 3
RATE_LIMIT_MAX_INSTANCES_ENV_VAR = "RATE_LIMIT_MAX_INSTANCES"


def per_instance_limit(intended_per_minute: int) -> str:
    raw = os.environ.get(RATE_LIMIT_MAX_INSTANCES_ENV_VAR)
    try:
        max_instances = int(raw) if raw is not None else DEFAULT_RATE_LIMIT_MAX_INSTANCES
    except ValueError:
        max_instances = DEFAULT_RATE_LIMIT_MAX_INSTANCES
    max_instances = max(max_instances, 1)
    # Ceiling division: rounds up so the per-instance limit never drops to
    # zero, at the cost of the true worst-case cluster total being able to
    # exceed intended_per_minute by a little (e.g. 10 -> 4/instance -> a
    # worst-case cluster total of 12, not 10) — still a real, meaningful
    # bound, not a cosmetic one.
    per_instance = math.ceil(intended_per_minute / max_instances)
    return f"{per_instance}/minute"


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
