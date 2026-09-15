export interface ProviderOption {
  id: string
  displayName: string
  local: boolean
  requiresApiKey: boolean
  requiresBaseUrl: boolean
  defaultBaseUrl?: string
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
