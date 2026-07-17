"""Per-IP rate limiting for public, cost-bearing endpoints (currently just
POST /cases/{id}/hint, which calls the OpenAI API on every request). This is
a separate concern from the domain-level HintPolicy (hint count per case per
player) — that limits how much of a single case a player can see; this
limits how fast any one caller can hit the endpoint at all, regardless of
case or player, which is what actually bounds OpenAI spend once the demo URL
is public.

Keys on X-Forwarded-For rather than the raw socket peer address: behind
Cloud Run's proxy layer, request.client.host reflects Cloud Run's own
internal hop, not the real caller — every request would look like the same
source, either never tripping the limit or (worse) rate-limiting every real
user as if they were one. Cloud Run sets X-Forwarded-For with the actual
client IP first in the chain. Falls back to the raw peer address when the
header is absent (local dev, tests).
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip)
