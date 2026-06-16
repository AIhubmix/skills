---
name: aihubmix-api
description: "Query and use AIHubMix API/model information from live sources. Use for Chinese or English requests about AIHubMix/AIHubmix/Aihubmix: model lists, latest models, model-family introductions, model IDs, pricing, context/max output, capabilities, providers or aliases such as GPT/OpenAI, Gemini/Google/谷歌, Claude/Anthropic/Opus/Sonnet, Qwen/通义/千问, Kimi/Moonshot/月之暗面, DeepSeek/深度求索, Doubao/豆包, GLM/智谱 when the context is AIHubMix; OpenAI-compatible/Anthropic/Gemini gateway calls; Windows PowerShell, macOS/Linux curl, JavaScript examples; aihubmix-openapi contract details; API keys/auth headers; and API error troubleshooting such as 400/401/403/404/429/5XX, garbled output, empty content, or X-Request-Id. Do not use for unrelated general model news or non-AIHubMix API questions unless the user asks to compare with AIHubMix."
---

# AIHubMix API

Use this skill to answer AIHubMix API questions through live model metadata,
the AIHubMix AI SDK provider package, the gateway OpenAPI contract, and
observed error responses. Do not maintain a static model/price table inside
the skill.

## Trigger Scope

Use this skill when the user asks, in Chinese or English, for any AIHubMix API
or AIHubMix-hosted model task. Common Chinese requests include asking to list
models, introduce the latest Google/Gemini or Moonshot/Kimi models, query
Qwen/GPT/Claude prices, or generate a Windows call example.

- Query models: model list, latest models, model-family introductions, Google
  or Gemini latest models, Moonshot or Kimi latest models, Qwen interface
  information, GPT 5.4 details, Opus 4.8 price.
- Compare model facts: price, context, max output, modalities, capabilities,
  endpoints, provider/developer, or model ID spelling.
- Generate usage examples: Windows PowerShell, macOS/Linux curl, JavaScript,
  AI SDK provider calls, OpenAI-compatible calls, Anthropic/Gemini-shaped
  gateway calls.
- Debug API calls: auth, API key, status codes, request body, empty response
  content, garbled terminal output, `X-Request-Id`, or gateway error body.
- Inspect gateway contracts: `aihubmix-openapi`, `openapi.json`,
  `contract.json`, auth schemes, endpoint paths, or response schemas.

Do not use this skill for general industry news, official vendor release notes,
or non-AIHubMix API usage unless the user explicitly asks to route, price,
compare, or call the model through AIHubMix.

## Data Sources

Use sources in this order:

1. Model metadata: `https://aihubmix.com/api/v1/models`
   - Use for model ID, display name, pricing fields, context length, max output,
     modality, endpoint/type, and feature tags.
   - Display pricing values exactly as returned. Use `USD / 1M tokens` as the
     default price unit unless `AIHUBMIX_PRICE_UNIT` is set for a team-confirmed
     override.
2. SDK/provider package: `@aihubmix/ai-sdk-provider@2.1.0`
   - Use for JavaScript examples, AI SDK provider surface, provider factory
     names, supported AI SDK features, default auth behavior, and SDK version
     checks.
   - Treat it as the source for SDK usage, not as the source for live model
     price, context, or availability data.
   - Prefer generated JS examples that import `aihubmix` from
     `@aihubmix/ai-sdk-provider` and `generateText` from `ai`.
   - Check for newer SDK versions only when the user asks, when the SDK source
     may affect the answer, or during acceptance validation. Never auto-install
     or auto-update this package.
3. Gateway contract: `AIhubmix/aihubmix-openapi`
   - Use `openapi.json`, `contract.json`, `gateway/auth.yml`,
     `gateway/errors.yml`, `PROTOCOLS.md`, and `examples/`.
   - Prefer a local checkout from `AIHUBMIX_OPENAPI_REPO`, the current workspace,
     or a nearby `aihubmix-openapi` directory.
   - If no local checkout exists, use `https://aihubmix.com/openapi.json`,
     `https://aihubmix.com/contract.json`, or ask the user for the repo path.
4. Observed response:
   - Use the actual HTTP status, JSON body, and `X-Request-Id` header for
     troubleshooting. Do not infer hidden upstream state without evidence.

Data-source rule: `/api/v1/models` plus `@aihubmix/ai-sdk-provider` plus
`aihubmix-openapi` is sufficient for this phase ("query + example generation +
troubleshooting entrypoints"). Keep `/api/v1/models` authoritative for model
facts, keep the npm SDK authoritative for JS SDK usage, and keep the OpenAPI
repo authoritative for gateway protocol contracts.

When answering the user, display only remote authoritative source addresses:
`https://aihubmix.com/api/v1/models` for model data,
`https://registry.npmjs.org/@aihubmix%2Fai-sdk-provider` for SDK package data,
`https://aihubmix.com/openapi.json`, `https://aihubmix.com/contract.json`, or
`https://github.com/AIhubmix/aihubmix-openapi` for gateway contracts. Do not
show local fixture paths, local script paths, local checkout paths, or
`C:\...` paths as data sources in user-facing answers. Local files are only for
offline validation and debugging.

## Helper Script

Prefer `scripts/aihubmix_api.py` for repeatable work. It uses only Python
standard library and supports live API data or local JSON fixtures.

Common commands:

```bash
python scripts/aihubmix_api.py list --limit 20
python scripts/aihubmix_api.py latest-report --limit 5
python scripts/aihubmix_api.py report <query>
python scripts/aihubmix_api.py get <model-id>
python scripts/aihubmix_api.py compare <model-a> <model-b> <model-c>
python scripts/aihubmix_api.py protocols --repo /path/to/aihubmix-openapi
python scripts/aihubmix_api.py error-contract --repo /path/to/aihubmix-openapi
python scripts/aihubmix_api.py sdk-check --version 2.1.0
python scripts/aihubmix_api.py sdk-info --version 2.1.0
python scripts/aihubmix_api.py example chat --model <model-id>
python scripts/aihubmix_api.py example chat --model <model-id> --lang python
python scripts/aihubmix_api.py troubleshoot --status 401 --body-file error.json --endpoint /v1/chat/completions --model <model-id> --repo /path/to/aihubmix-openapi
```

For offline validation or tests, pass a model fixture:

```bash
python scripts/aihubmix_api.py list --source references/sample-models.json
python scripts/aihubmix_api.py get sample-chat-small --source references/sample-models.json
python scripts/aihubmix_api.py compare sample-chat-small sample-chat-large --source references/sample-models.json
```

## Workflows

### List Models

When the user asks which models AIHubMix supports, run:

```bash
python scripts/aihubmix_api.py list --limit 50
```

Return a compact table with model ID, name, provider/developer, context,
max output, and type/endpoint. If the user asks for a category, use `--query`
or filter the JSON output.

When the user asks to introduce a model family or query such as `qwen3.5`,
run:

```bash
python scripts/aihubmix_api.py report qwen3.5
```

Use `report` for natural-language aliases and provider nicknames too. The
helper normalizes common Chinese and English aliases such as `月之暗面`,
`Kimi`, `Moonshot`, `谷歌`, `Google`, `Gemini`, `Claude Opus 最新`,
`通义`, `千问`, `Qwen`, `豆包`, `智谱`, `DeepSeek`, and related provider
names before matching model metadata. Alias normalization only affects search
terms and relevance ranking; never use it as a source for model price, context,
availability, or protocol facts.

Use the report output as source data, not as the final user-facing answer. For
call-intent questions such as "怎么调用", "how to call/use", "调用示例", or
"API example" with a model family or version, first list only the matched
`model_id` values. Do not include prices, context, max output, developer IDs,
features, modalities, raw endpoints, or notes unless the user asks for model
details. Then identify the likely default model ID to copy and provide runnable
examples. Choose the protocol and auth shape internally; do not present a
separate interface/protocol/endpoint/auth explanation block unless the user
asks for endpoint details or troubleshooting.
For report examples, let the helper choose a protocol from the matched model:
`gemini_api` -> Gemini native, `claude_api` -> Claude/Anthropic messages,
`responses` -> OpenAI Responses, `chat_completions` or plain `llm` -> OpenAI
chat. For image, embedding, audio, or video models, do not force a chat
example; verify the endpoint contract first.
Do not answer with placeholders such as "not expanded", "not queried",
"pending lookup", "omitted", or "etc." for fields that can be read from the
models API. If a lookup actually fails, state the failure reason and which
source failed.

When the user asks for "latest N models with price/context/example", run:

```bash
python scripts/aihubmix_api.py latest-report --limit 5
```

Use the report output directly unless the user asks for a different format.
The report must include data source, query time, latest-definition, price unit,
pricing values, context length, max output, notes, and OS-specific command-line
plus JavaScript examples.
For this command, preserve the original order returned by `/api/v1/models`.
Do not sort by model ID before selecting the first N records.

Use `Price unit: USD / 1M tokens` by default. Do not leave price values naked.
If the team wants to override the default unit, set `AIHUBMIX_PRICE_UNIT` before
running the script, for example `AIHUBMIX_PRICE_UNIT="USD / 1M tokens"`.

### Query One Model

When the user provides a model ID or asks about one model, run:

```bash
python scripts/aihubmix_api.py get <model-id>
```

Return model ID, display name, provider/developer, context, max output, pricing,
types/endpoints, and features/modalities. If the model is not found, do not
guess; tell the user it was not found in the selected model source.

### Compare Models

When the user asks which model is cheaper, larger-context, or better suited
for a use case, run:

```bash
python scripts/aihubmix_api.py compare <model-a> <model-b> ...
```

Compare only fields returned by the model API. Always show the price unit
statement. Make recommendations only after separating facts from assumptions.
If pricing units are unclear, rank only when the returned fields are directly
comparable.

## Output Format

Default model outputs must match the user's intent before showing details.
For call-intent questions about a model family or version, start with a compact
model-ID list only, then the likely default model ID and the call examples.
Keep pricing, context, max output, features, modalities, developer IDs, raw
endpoints, protocol labels, auth header explanations, and trace details out of
the first answer unless the user asks for details, comparison, pricing, context,
endpoint information, troubleshooting, or a full report.

For model-detail questions, be user-facing first and technical second. Start
with a short overview of the specific fields the user asked about, then put raw
fields and trace details after that overview.

For model reports, use this structure:

```text
AIHubMix Model Report
- Data source: <url or file>
- Query time: <local ISO timestamp>
- Latest definition: <created_at/updated_at if available, otherwise source order from /api/v1/models>
- Price unit: <configured unit, defaulting to "USD / 1M tokens">

| # | model_id | name | developer_id | pricing | context | max_output | type | callable entrypoints | features | notes |

OpenAI-Compatible Call Example
<OS-specific command-line example, Python example, and JavaScript example>
```

Rules:

- Never output pricing numbers without a price-unit line.
- For model-family or alias queries, include the `Normalized query terms` line
  from the helper output so users can see how nicknames such as `月之暗面` or
  `谷歌最新` were resolved.
- Display pricing object keys exactly as returned, such as `input`, `output`,
  `cache_read`, and `cache_write`.
- Use compact token notation for human-facing token fields: `64K`, `200K`,
  `991K`, `1M`. Keep raw numeric values available through `--json` when needed.
- If a structured field is `0` or empty, show it as returned and add a note only
  when the model description provides relevant context.
- Include the data source and query time for every "latest" report.
- Data sources shown to users must be remote URLs, not local files. Even when a
  local fixture or local `aihubmix-openapi` checkout was used for validation,
  cite the corresponding remote authoritative source in the answer.
- Write query time with an explicit timezone label. Prefer
  `YYYY-MM-DD HH:mm:ss (local time, UTC+08:00)` or Chinese prose such as
  `查询时间：2026-06-16 10:48:51（本地时间，UTC+08:00）`. Do not leave a bare
  offset like `+08:00` or `+8` without explaining that it is the UTC offset.
- When outputting examples for call-intent questions, default to three formats:
  the OS-specific command-line block, Python, and JavaScript. Only output a
  single format when the user explicitly asks for one.
- Before every example code block, write one short connective sentence that
  explains who should use that example and what it does, such as "下面这个
  PowerShell 示例适合在 Windows 终端里直接测试；它会读取
  AIHUBMIX_API_KEY，发送一次请求，并打印模型回复。" Do not jump from a
  heading like `Windows PowerShell` directly into code.
- When an example depends on `AIHUBMIX_API_KEY`, include the exact environment
  variable setup command before the example. On Windows PowerShell use
  `$env:AIHUBMIX_API_KEY = Read-Host "Paste AIHubMix API Key"`; on macOS/Linux
  use `export AIHUBMIX_API_KEY="sk-..."`. Do not merely say "set the
  environment variable".
- When showing multiple optional model IDs, add one sentence explaining that
  users can call a different model by replacing the `model` or `model_id` value
  in the examples with another listed ID.
- Avoid ambiguous status phrases. Do not write "not expanded", "not queried",
  "pending lookup", or similar wording for model rows. Either show the field
  from the API, show `-` when the API field is empty, or explicitly report the
  API/source error.
- For call-intent questions, do not show standalone text blocks such as
  "Suggested Gemini Native Endpoint", "Default recommend interface",
  `POST <url>`, or `Header: <auth>`. Put the URL and auth header only inside
  runnable code examples, where they are necessary.
- Do not expose raw endpoint tokens as the only explanation. Map common endpoint
  values to human-readable labels:
  - `chat_completions` -> `OpenAI-compatible chat`
  - `gemini_api` -> `Gemini native`
  - `claude_api` -> `Claude/Anthropic-compatible`
  Keep the raw endpoint value only as a secondary trace field when useful.
- When `endpoints` is empty for a plain `llm`, write `not declared; use
  OpenAI-compatible chat example by default` instead of `endpoint field is
  empty`.
- When `endpoints` is empty for image/video/audio or mixed-type models, write
  `not declared; choose endpoint by model type and verify against contract`.

### Generate API Examples

When the user asks for call examples, choose the protocol shape internally:

- OpenAI chat: `/v1/chat/completions`
- OpenAI responses: `/v1/responses`
- Anthropic shape: `/v1/messages`
- Gemini shape: `/gemini/v1beta/models/{model}:generateContent`

Do not explain the selected protocol to the user unless they ask which endpoint
or protocol is being used.

Generate examples with:

```bash
python scripts/aihubmix_api.py example chat --model <model-id>
python scripts/aihubmix_api.py example responses --model <model-id> --lang json
python scripts/aihubmix_api.py example messages --model <model-id>
python scripts/aihubmix_api.py example gemini --model <model-id>
```

Default example output must contain three formats:

1. Command-line example
   - Auto-detect the current OS.
   - On Windows, output a PowerShell `Invoke-RestMethod` example.
   - On macOS/Linux, output a shell `curl` example.
   - The command-line example should be paste-ready, prompt for the API key
     instead of embedding a real key, and print the main model reply content
     directly after the request.
   - On Windows, assign `Invoke-RestMethod` to `$response` and print
     `$response.choices[0].message.content` with `[Console]::WriteLine(...)`.
   - On Windows, set UTF-8 before the request to avoid mojibake in Chinese or
     other non-ASCII output:
     `$OutputEncoding = [System.Text.Encoding]::UTF8`,
     `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`, and
     `[Console]::InputEncoding = [System.Text.Encoding]::UTF8`.
   - On macOS/Linux, pipe the JSON response through a standard-library parser
     such as `python3 -c` to print `choices[0].message.content`.
2. JavaScript example
   - For default chat/text examples, use the AIHubMix AI SDK provider:
     import `aihubmix` from `@aihubmix/ai-sdk-provider` and `generateText`
     from `ai`.
   - For non-OpenAI-shaped protocol examples, use `fetch` with the correct
     endpoint and auth header.
   - Print the main model reply content directly, such as `console.log(text)`.
3. Python example
   - For OpenAI-compatible chat/text examples, use the OpenAI Python client
     with `base_url="https://aihubmix.com/v1"` and
     `api_key=os.environ["AIHUBMIX_API_KEY"]`.
   - For non-OpenAI-shaped protocol examples, use a standard HTTP client and
     the correct endpoint/auth header.
   - Print the main model reply content directly.

Use `AIHUBMIX_API_KEY` as the environment variable/key prompt label. Do not
store, print, or paste real API keys into generated examples. If the user
explicitly provides a key and asks to inline it, refuse to echo the secret and
provide a paste-ready prompt-based example instead.

For test commands, do not leave users with only a folded response object such
as PowerShell's `choices : {@{...}}`. Always print the primary content field
and optionally include a commented full-response debug line.

### Check SDK Version

When the user asks whether the SDK source is enough, what the SDK supports,
whether the package is current, or whether to upgrade, run:

```bash
python scripts/aihubmix_api.py sdk-check --version 2.1.0
python scripts/aihubmix_api.py sdk-info --version 2.1.0
python scripts/aihubmix_api.py sdk-check --project /path/to/project --version 2.1.0
python scripts/aihubmix_api.py sdk-info --project /path/to/project --version 2.1.0
```

Rules:

- Report installed version, target version, npm latest version, and source.
- Always state `Auto update: not performed`.
- Do not run `npm install`, `npm update`, or package-manager writes unless the
  user explicitly confirms the target project and version.
- If a newer version exists, say to review the changelog before updating. Do
  not imply that every query should update the SDK.
- Use `sdk-info` to report SDK/provider capability surface, including
  `chat`, `responses`, `embedding`, `image`, `transcription`, `speech`, tools,
  `AIHUBMIX_API_KEY`, base URL, and header/routing defaults.
- Existing sources are sufficient for SDK capability output because
  `@aihubmix/ai-sdk-provider` exposes these methods and defaults in its package
  type declarations and built output. Treat `sdk-info` as SDK usage metadata,
  not live model availability or pricing.
- For offline acceptance, run `sdk-info --source baseline --version 2.1.0`.

### Inspect Protocol Contract

When the user asks what endpoints, auth schemes, or request bodies are exposed,
use the OpenAPI repo:

```bash
python scripts/aihubmix_api.py protocols --repo /path/to/aihubmix-openapi
python scripts/aihubmix_api.py error-contract --repo /path/to/aihubmix-openapi
```

If deeper details are needed, inspect these files from the repo:

```bash
rg "gatewayBearer|gatewayAnthropicKey|gatewayGeminiKey|pathSecurity" gateway/auth.yml
rg "GatewayError|responseOverrides|X-Request-Id" gateway/errors.yml
rg "/v1/chat/completions|/v1/responses|/v1/messages|generateContent" PROTOCOLS.md
```

### Troubleshoot Errors

When the user shares an error, collect endpoint, model ID, status, error body,
and `X-Request-Id`. Then run:

```bash
python scripts/aihubmix_api.py troubleshoot --status <status> --body-file error.json --endpoint <path> --model <model-id> --repo /path/to/aihubmix-openapi
```

Use `error-contract` when the user asks where the error structure or categories
are defined. It reads `gateway/errors.yml` and reports the `GatewayError` body
shape, status response descriptions, and `X-Request-Id` header rule. Existing
sources are sufficient for this phase because `gateway/errors.yml` is the
gateway contract source; use live error responses only as observed evidence for
one request.

For more detail, read `references/troubleshooting.md`.

## Auth Matrix

- OpenAI-shaped endpoints: `Authorization: Bearer $AIHUBMIX_API_KEY`.
- Anthropic-shaped `/v1/messages`: `x-api-key: $AIHUBMIX_API_KEY`; Bearer is a
  compatibility fallback.
- Gemini-shaped `/gemini/v1beta/...`: `x-goog-api-key: $AIHUBMIX_API_KEY` or
  `?key=$AIHUBMIX_API_KEY`.

## Boundaries

- Do not hardcode live model lists, prices, context lengths, provider status,
  or availability claims in this skill.
- Do not maintain a manual table of model aliases to model facts. Alias rules
  may map user wording to provider/model-family search terms only; all factual
  fields must still come from `/api/v1/models`, the SDK package, the gateway
  contract, or an observed response.
- Do not save API keys into skill files, repos, examples, or logs.
- Do not treat model existence in `/api/v1/models` as proof that the current
  user's key has permission to call it.
- Do not change gateway contracts or generated OpenAPI artifacts unless the
  user explicitly asks for contract development work.
- Do not resolve billing disputes from model metadata alone; preserve returned
  pricing fields, request IDs, and raw error bodies.

## Acceptance Checks

From the skill directory, run:

```bash
python scripts/aihubmix_api.py list --source references/sample-models.json
python scripts/aihubmix_api.py report sample-chat --source references/sample-models.json
python scripts/aihubmix_api.py report 月之暗面最新 --source references/sample-models.json
python scripts/aihubmix_api.py report 谷歌最新 --source references/sample-models.json
python scripts/aihubmix_api.py report "Claude Opus 最新" --source references/sample-models.json
python scripts/aihubmix_api.py report 通义千问 --source references/sample-models.json
python scripts/aihubmix_api.py get sample-chat-small --source references/sample-models.json
python scripts/aihubmix_api.py compare sample-chat-small sample-chat-large --source references/sample-models.json
python scripts/aihubmix_api.py example chat --model sample-chat-small
python scripts/aihubmix_api.py sdk-check --offline --version 2.1.0
python scripts/aihubmix_api.py sdk-info --source baseline --version 2.1.0
python scripts/aihubmix_api.py protocols --repo /path/to/aihubmix-openapi
python scripts/aihubmix_api.py error-contract --repo /path/to/aihubmix-openapi
python scripts/aihubmix_api.py troubleshoot --status 401 --body "{\"error\":{\"message\":\"bad key\",\"type\":\"authentication_error\"}}" --repo /path/to/aihubmix-openapi
```

Then validate the skill structure with the skill creator validator.
