class AIProviderError(Exception):
    """Base class for AI provider failures. See docs/AI_CONTRACTS.md #13."""


class AIProviderUnavailableError(AIProviderError):
    """The provider could not be reached or rejected the request (auth, network)."""


class AIInvalidOutputError(AIProviderError):
    """The provider's response failed schema/business validation."""
