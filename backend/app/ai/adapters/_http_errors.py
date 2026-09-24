"""Shared `httpx` error -> `AIProviderUnavailableError` translation for
every wire adapter (docs/TASKS.md T144).

Plain `str(httpx.HTTPStatusError)` is only the status line ("Client error
'400 Bad Request' for url '...'") -- it never includes the response body,
which is exactly where a provider puts the one piece of information that
actually explains a 4xx (invalid model name, malformed request field,
unsupported parameter). Every adapter used to raise with only the status
line, making a real rejection indistinguishable from a network outage and
impossible to self-diagnose from the error message alone. A connection-
level failure (`ConnectError`, `TimeoutException`, ...) has no response to
read, so those still fall back to the plain message.
"""

import httpx

from app.ai.errors import AIProviderUnavailableError


def provider_unavailable_error(exc: httpx.HTTPError) -> AIProviderUnavailableError:
    if isinstance(exc, httpx.HTTPStatusError):
        return AIProviderUnavailableError(f"{exc}: {exc.response.text}")
    return AIProviderUnavailableError(str(exc))
