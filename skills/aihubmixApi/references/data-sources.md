# Data Sources

Use this module whenever the answer depends on where AIHubMix data comes from,
whether local data is bundled, whether a fact can be trusted, or how API keys
should be handled.

## Source Priority

1. Model metadata: `https://aihubmix.com/api/v1/models`
   - Use for model ID, display name, pricing fields, context length, max
     output, modality, endpoint/type, and feature tags.
   - Keep this source authoritative for live model facts.
   - Display pricing exactly as returned. Use `USD / 1M tokens` as the default
     user-facing price unit unless `AIHUBMIX_PRICE_UNIT` is set for a
     team-confirmed override.
2. SDK/provider package: `@aihubmix/ai-sdk-provider@2.1.0`
   - Use for JavaScript SDK examples, AI SDK provider surface, provider
     factory names, supported AI SDK features, default auth behavior, and SDK
     version checks.
   - Treat it as SDK usage metadata, not as the source for model price,
     context, or availability.
   - Source URL:
     `https://registry.npmjs.org/@aihubmix%2Fai-sdk-provider`
3. Gateway contract: `AIhubmix/aihubmix-openapi`
   - Use `openapi.json`, `contract.json`, `gateway/auth.yml`,
     `gateway/errors.yml`, `PROTOCOLS.md`, and `examples/`.
   - Prefer remote user-facing source URLs:
     `https://aihubmix.com/openapi.json`,
     `https://aihubmix.com/contract.json`, and
     `https://github.com/AIhubmix/aihubmix-openapi`.
   - Local checkouts can be used for inspection, but do not cite local paths as
     data sources in user-facing answers.
4. Observed response:
   - Use the actual HTTP status, JSON body, and `X-Request-Id` header for
     troubleshooting a specific request.
   - Do not infer hidden upstream state without evidence.

## No Local Data Rule

Do not bundle model lists, prices, context windows, provider availability, SDK
capabilities, or gateway schemas as local truth. The skill may include:

- Procedural rules.
- Endpoint routing rules.
- Helper scripts.
- Troubleshooting guidance.
- Output format requirements.

The skill must not include local static copies of easy-to-expire AIHubMix model
facts.

## User-Facing Source Rules

When citing sources in an answer, show only remote authoritative addresses:

- `https://aihubmix.com/api/v1/models`
- `https://registry.npmjs.org/@aihubmix%2Fai-sdk-provider`
- `https://aihubmix.com/openapi.json`
- `https://aihubmix.com/contract.json`
- `https://github.com/AIhubmix/aihubmix-openapi`

Do not show local fixture paths, local script paths, local checkout paths,
cache directories, or Windows paths such as `C:\...` as data sources.

## API Key Handling

Default to `AIHUBMIX_API_KEY`.

- For examples, prompt for the key or read from the environment.
- Never paste a real API key into generated code, project files, examples,
  logs, final answers, or skill files.
- When editing a project, add `.env.example` placeholders only.
- If the user explicitly opts in to a local credential file, use a private
  user-level path rather than the project or skill folder:
  - Windows: `%USERPROFILE%\.aihubmix\credentials.env`
  - macOS/Linux: `~/.aihubmix/credentials.env`
- Recommended read order for future credential helpers:
  environment variable -> user credential file -> project `.env.local/.env`
  -> prompt the user.
- Mask keys in output, for example `sk-...1234`.

## Sufficiency For Current Phase

For the current skill scope, these sources are sufficient:

- `/api/v1/models` for model lookup, price, context, max output, capability
  tags, and endpoint hints.
- `@aihubmix/ai-sdk-provider` for JavaScript SDK usage and SDK upgrade checks.
- `aihubmix-openapi` for gateway protocol contracts, auth schemes, and error
  envelopes.
- Actual error responses for one-request troubleshooting evidence.
