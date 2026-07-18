"""Shared field constraints for request-body identifiers (player_id,
suspect_id). Both are caller-supplied strings that flow straight into
Firestore document paths and query filters — bounding their length and
character set is cheap, real input validation, not just documentation.
64 chars comfortably covers a UUID4 (36 chars, the actual player_id shape —
see CreatePlayer) and every existing suspect_id ("suspect_1" etc.) with
plenty of headroom; the character class matches both shapes exactly.
"""

from typing import Annotated

from pydantic import Field

IdField = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
