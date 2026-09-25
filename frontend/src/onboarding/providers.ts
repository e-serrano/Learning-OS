export interface ProviderOption {
  id: string
  displayName: string
  local: boolean
  requiresApiKey: boolean
  requiresBaseUrl: boolean
  defaultBaseUrl?: string
  /** Suggested starting model + a one-line reasoning-task alternative,
   * shown as a prefill/hint in the wizard's Model field -- only set for
   * providers with a known, sensible free/default tier (currently just
   * `openrouter`, docs/TASKS.md T148, user request). Other providers keep
   * today's blank field: no similarly well-known free default exists for
   * OpenAI/Anthropic, and Ollama/mock's model choice already depends on
   * what the user has pulled locally. */
  defaultModel?: string
  reasoningModelHint?: string
  /** Suggested fallback model + alternative, shown in the wizard's
   * optional "Fallback model" field -- same reasoning-heavy-only scoping
   * as above. Free-tier models on a shared provider (OpenRouter) rate-limit
   * independently per model, so a second free model is a real, useful
   * automatic fallback (`app/ai/provider_factory.py` wires it into
   * `RetryingProvider`) rather than retrying the same exhausted one. */
  defaultFallbackModel?: string
  fallbackModelHint?: string
}

/** Mirrors backend/app/ai/provider_registry.py -- see docs/AI_CONTRACTS.md #16-17. */
export const PROVIDER_OPTIONS: ProviderOption[] = [
  {
    id: 'mock',
    displayName: 'Mock (offline, deterministic)',
    local: true,
    requiresApiKey: false,
    requiresBaseUrl: false,
  },
  {
    id: 'ollama',
    displayName: 'Ollama (local)',
    local: true,
    requiresApiKey: false,
    requiresBaseUrl: true,
    defaultBaseUrl: 'http://localhost:11434',
  },
  {
    id: 'openai',
    displayName: 'OpenAI',
    local: false,
    requiresApiKey: true,
    requiresBaseUrl: false,
  },
  {
    id: 'anthropic',
    displayName: 'Anthropic / Claude',
    local: false,
    requiresApiKey: true,
    requiresBaseUrl: false,
  },
  {
    id: 'openrouter',
    displayName: 'OpenRouter',
    local: false,
    requiresApiKey: true,
    requiresBaseUrl: true,
    defaultBaseUrl: 'https://openrouter.ai/api/v1',
    defaultModel: 'qwen/qwen3.8-27b:free',
    reasoningModelHint: 'nvidia/nemotron-3-ultra:free',
    defaultFallbackModel: 'openrouter/free',
    fallbackModelHint: 'deepseek/deepseek-r1:free',
  },
  {
    id: 'nvidia_nim',
    displayName: 'NVIDIA NIM/API',
    local: false,
    requiresApiKey: true,
    requiresBaseUrl: true,
  },
  {
    id: 'openai_compatible',
    displayName: 'OpenAI-compatible',
    local: false,
    requiresApiKey: false,
    requiresBaseUrl: true,
  },
]
