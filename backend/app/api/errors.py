"""Shared error-envelope helper for API routes (docs/TASKS.md T108,
docs/API_SPEC.md #11: `{"error": {"code", "message", "details"}}`).

Every route module from T096 onward defined its own byte-identical
local `_error()` helper -- T101's own note flagged this as "the natural
place to consolidate ... if the pattern repeats enough by T108", and by
T107 it had repeated across 11 files. Collapsed here into one function,
imported everywhere, with `status_code` a required argument (no
default): `onboarding.py`'s own local copy (predating this convention,
from T025) gave it a `= 400` default, which silently mapped
`SESSION_STATE_ERROR` to HTTP 400 in four places while every later
route maps the same normative code to 409 -- a real inconsistency this
consolidation fixes by construction, since there is no longer anywhere
for a divergent default to hide.
"""

from fastapi import HTTPException

NORMATIVE_ERROR_CODES = frozenset(
    {
        "VALIDATION_ERROR",
        "NOT_FOUND",
        "CONFLICT",
        "VAULT_UNAVAILABLE",
        "VAULT_CONFLICT",
        "AI_UNAVAILABLE",
        "AI_INVALID_OUTPUT",
        "SESSION_STATE_ERROR",
        "PERMISSION_DENIED",
    }
)
"""docs/API_SPEC.md #11's closed list of known error codes."""


def api_error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )
