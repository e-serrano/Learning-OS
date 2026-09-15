from pydantic import BaseModel

from app.ai.provider_registry import ProviderId, get_provider_descriptor


class CapabilityCheckResult(BaseModel):
    """Result of validating a provider configuration -- see docs/AI_CONTRACTS.md #19.

    Never carries credential values (docs/AI_CONTRACTS.md #20).
    """

    ok: bool
    provider_id: ProviderId
    reason: str | None = None


def check_provider_capability(
    provider_id: ProviderId,
    model: str | None,
    base_url: str | None,
    credential: str | None,
) -> CapabilityCheckResult:
    """Structural pre-check: required credential/base_url/model are present.

    Takes primitives rather than AIProviderConfig so app.ai never depends on
    app.config (app.config already depends on app.ai for ProviderId).

    This never sends vault content, and never touches the network -- it only
    validates the configuration against the provider's declared requirements
    (docs/AI_CONTRACTS.md #16). Live connection/structured-output validation
    is added once each provider's real adapter lands (T051-T056); until
    then, callers should treat `ok=True` as "configuration is well-formed",
    not "provider is confirmed reachable".
    """
    descriptor = get_provider_descriptor(provider_id)

    if descriptor.requires_api_key and not credential:
        return CapabilityCheckResult(
            ok=False,
            provider_id=provider_id,
            reason="Missing required API credential",
        )
    if descriptor.requires_base_url and not base_url:
        return CapabilityCheckResult(
            ok=False,
            provider_id=provider_id,
            reason="Missing required base_url",
        )
    if not model:
        return CapabilityCheckResult(
            ok=False,
            provider_id=provider_id,
            reason="Missing model",
        )
    if not descriptor.supports_structured_output:
        return CapabilityCheckResult(
            ok=False,
            provider_id=provider_id,
            reason="Provider does not declare structured-output support",
        )

    return CapabilityCheckResult(ok=True, provider_id=provider_id)
