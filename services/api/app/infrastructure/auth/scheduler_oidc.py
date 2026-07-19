"""Verifies Google-signed OIDC ID tokens from the Cloud Scheduler job that
drives POST /admin/cases/publish-next-daily (see ADR-0006's Cloud Scheduler
amendment) — the structural replacement for that job's earlier static
X-Admin-Token header, which a `gcloud scheduler jobs create/update` command
turned out to echo back to stdout in plaintext (a real leak, see the ADR).

With --oidc-service-account-email configured on the Scheduler job, GCP
itself mints a short-lived, Google-signed ID token on every invocation and
sends it as `Authorization: Bearer <token>` — no secret value is ever
stored in the job resource for a `describe` call (or an accidental stdout
echo) to expose. Verification here checks three things, all required: the
token's signature (against Google's own public certs, fetched over HTTPS
by the google-auth library itself), the `aud` claim (so a token minted for
some other Cloud Run service can't be replayed against this one), and the
`email`/`email_verified` claims (so only the specific service account this
project created for the scheduler is trusted — not just "any valid Google
OIDC token").

Fails closed, deliberately, matching require_admin's own "disabled by
default" pattern: if either env var is unset, verification is skipped
entirely and every token is rejected — this mechanism cannot be
accidentally left half-configured into an open door. Static-header admin
auth (app/api/dependencies.py's require_admin) is untouched and remains
the path for human/manual admin API use.
"""

import logging
import os

from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token

SCHEDULER_SERVICE_ACCOUNT_EMAIL_ENV_VAR = "SCHEDULER_SERVICE_ACCOUNT_EMAIL"
SCHEDULER_OIDC_AUDIENCE_ENV_VAR = "SCHEDULER_OIDC_AUDIENCE"

logger = logging.getLogger(__name__)

# Module-level: google-auth's Request wraps a requests.Session for fetching
# Google's public signing certs, which it already caches internally across
# calls — one shared instance avoids re-creating that session (and losing
# its cert cache) on every single request.
_transport_request = google_auth_requests.Request()


def verify_scheduler_oidc_token(token: str) -> bool:
    expected_email = os.environ.get(SCHEDULER_SERVICE_ACCOUNT_EMAIL_ENV_VAR)
    audience = os.environ.get(SCHEDULER_OIDC_AUDIENCE_ENV_VAR)
    if not expected_email or not audience:
        return False

    try:
        claims = id_token.verify_oauth2_token(token, _transport_request, audience=audience)
    except (GoogleAuthError, ValueError) as exc:
        # ValueError covers malformed/non-JWT input; GoogleAuthError covers
        # expired/bad-signature/wrong-issuer — both are "not a valid
        # scheduler token", never a reason to 500 the request.
        logger.warning("rejected scheduler OIDC token: %s", exc)
        return False

    return bool(claims.get("email_verified")) and claims.get("email") == expected_email
