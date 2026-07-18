"""TTL field computation for Firestore documents.

Firestore's native TTL feature automatically deletes a document once a
designated Timestamp field on it is in the past — but Firestore doesn't
compute that field itself; the application has to write it, and a
separate one-time admin action (`gcloud firestore fields ttls update`,
documented in docs/operations.md) has to point a TTL policy at it per
collection group. This module is the application-side half only: writing
a correct `expireAt` value onto documents that should eventually be
deleted (case_attempts, hint_requests, rate_limits — see task 13 of the
security/ops audit). Without the gcloud-side policy too, `expireAt` is
just an inert field that sits there forever.

Retention lengths chosen for what's actually useful for this project's
attempts/hints (real player history, worth keeping a while for anyone
looking back at how the demo performed) versus its daily rate-limit
counters (worthless after the day they were for).
"""

from datetime import datetime, timedelta

ATTEMPT_AND_HINT_RETENTION = timedelta(days=180)
RATE_LIMIT_RETENTION = timedelta(days=7)


def expire_at(base: datetime | None, retention: timedelta) -> datetime | None:
    """None in, None out — a document whose created_at somehow wasn't set
    gets no expireAt rather than one computed from an arbitrary fallback
    time; better to never expire it than to guess wrong and delete real
    data early."""
    return base + retention if base is not None else None
