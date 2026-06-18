---
name: aihubmix-api
description: "Integrate, query, and use AIHubMix API/model access from live sources. Use for Chinese or English requests about adding AIHubMix to an app or project, generating runnable SDK/API code, selecting model IDs, listing latest models, model-family introductions, pricing, context/max output, capabilities, providers or aliases such as GPT/OpenAI, Gemini/Google/谷歌, Claude/Anthropic/Opus/Sonnet, Qwen/通义/千问, Kimi/Moonshot/月之暗面, DeepSeek/深度求索, Doubao/豆包, GLM/智谱 when the context is AIHubMix; OpenAI-compatible/Anthropic/Gemini gateway calls; Windows PowerShell, macOS/Linux curl, JavaScript and Python examples; aihubmix-openapi contract details; API keys/auth headers; and API error troubleshooting such as 400/401/403/404/429/5XX, garbled output, empty content, or X-Request-Id. Do not use for unrelated general model news or non-AIHubMix API questions unless the user asks to compare with, route through, or call the model via AIHubMix."
---

# AIHubMix API

Use this skill to help developers integrate AIHubMix without reading the
website first. Prefer a runnable path: inspect the user's project when files
are available, choose the right SDK or gateway protocol, add or generate
minimal code, include environment setup, and show how to verify the call.

Keep volatile facts out of the skill. Model IDs, prices, context windows,
availability, SDK capabilities, and gateway schemas must come from live or
authoritative remote sources.

## Module Map

Load only the module needed for the user's request:

- `references/data-sources.md`: source priority, remote URLs, no-local-data
  rules, credential handling boundaries.
- `references/model-query.md`: list models, report one family, latest models,
  price/context comparison, alias matching, and model-report output.
- `references/integration.md`: project integration workflow, dependency/env
  setup, reusable client/route guidance, and verification style.
- `references/protocols-and-examples.md`: endpoint matrix, Anthropic
  Compatible `/v1/messages`, Google Vertex/Gemini Compatible
  `generateContent`, protocol selection, and example generation rules.
- `references/sdk.md`: `@aihubmix/ai-sdk-provider` usage, capability checks,
  and version-check policy.
- `references/troubleshooting.md`: API error troubleshooting, GatewayError
  contract, status-code guidance, and `X-Request-Id`.
- `references/cli.md`: the `aihubmix` CLI — authenticated account data (balance,
  API keys, and the models the user's token can actually call).
- `references/acceptance.md`: local validation commands for the skill.

## Default Workflow

1. Identify the user's intent: integrate a project, query model information,
   generate standalone examples, compare models, inspect protocol contracts,
   check SDK usage, or troubleshoot an error.
2. Read the relevant reference module from the module map above.
3. Prefer `scripts/aihubmix_api.py` for repeatable data lookup, example
   generation, SDK inspection, protocol inspection, and troubleshooting.
4. Use remote authoritative sources in user-facing answers:
   - Model data: `https://aihubmix.com/api/v1/models`
   - SDK package data:
     `https://registry.npmjs.org/@aihubmix%2Fai-sdk-provider`
   - Gateway contracts: `https://aihubmix.com/openapi.json`,
     `https://aihubmix.com/contract.json`, and
     `https://github.com/AIhubmix/aihubmix-openapi`
5. Do not show local script paths, local checkout paths, fixtures, caches, or
   `C:\...` paths as data sources in user-facing answers.

## Helper Script

Use the script from the skill directory. It uses Python standard library and
does not ship local model/price/context data.

```bash
python scripts/aihubmix_api.py doctor --model <model-id> --image
python scripts/aihubmix_api.py candidates --capability vision   # image-gen | video | audio-tts | audio-stt | embedding | rerank
python scripts/aihubmix_api.py candidates --capability vision --mine   # only models YOUR token can call (needs aihubmix CLI + login)
python scripts/aihubmix_api.py install-cli      # install the companion aihubmix CLI (official per-OS installer)
python scripts/aihubmix_api.py list --limit 20
python scripts/aihubmix_api.py latest-report --limit 5
python scripts/aihubmix_api.py report <query>
python scripts/aihubmix_api.py get <model-id>
python scripts/aihubmix_api.py compare <model-a> <model-b> <model-c>
python scripts/aihubmix_api.py example chat --model <model-id>
python scripts/aihubmix_api.py example messages --model <model-id>
python scripts/aihubmix_api.py example gemini --model <model-id>
python scripts/aihubmix_api.py protocols
python scripts/aihubmix_api.py error-contract
python scripts/aihubmix_api.py sdk-check --version 2.1.0
python scripts/aihubmix_api.py sdk-info --version 2.1.0
python scripts/aihubmix_api.py troubleshoot --status 401 --body-file error.json --endpoint /v1/chat/completions --model <model-id>
```

The `--source` option is only for one-off debugging with caller-provided JSON.
Do not add bundled model fixtures to the skill.

## Onboarding, Capabilities, And Image Input

These commands target the most common onboarding friction: a bad key found too
late, and picking a model for a capability (image input, image generation,
video, audio, embeddings…).

- Preflight a key before wiring with `doctor`. It validates auth with a real
  minimal chat call (the public `/v1/models` list does NOT require auth and
  cannot validate a key), and optionally smoke-tests text and image input on a
  chosen model. It prints a `✓/✗` checklist, exits non-zero on failure, masks
  the key, and redacts keys from upstream error bodies. Run it when the user
  provides a key, switches keys, or hits auth/`401` errors. Pass `--model <id>`
  (and `--image`) to also confirm a specific model works:
  - `doctor` — verify the key only (auth probe via a default model).
  - `doctor --model <id>` — also confirm that model is callable.
  - `doctor --model <id> --image` — also probe image input on that model.
- For "which model can do X" questions (X = image input, image generation,
  video, TTS/STT, embedding, rerank), do NOT assert a single model from
  `/api/v1/models` metadata — its modality field is unreliable (some capable
  models lack the tag; some incapable ones carry it). Run
  `candidates --capability <X>` (aliases accepted, e.g. `多模态`, `t2i`, `生图`)
  to get a broad candidate range with a `signal` column, present or reason over
  it, let the model choose what fits the task, then confirm the choice with
  `doctor` (e.g. `doctor --model <id> --image` for vision). The script
  intentionally picks no default. `vision-candidates` aliases
  `candidates --capability vision`.
- Output language defaults to English (neutral). Pass the global `--lang zh` (or
  set `AIHUBMIX_LANG=zh`) for Chinese status lines and labels. `protocols` and
  `error-contract` read the live OpenAPI spec remotely — there is no local repo.

## Account And Auth (aihubmix CLI)

`scripts/aihubmix_api.py` only sees PUBLIC data. For anything account-specific —
the user's **balance**, their **API keys**, or **which models their token can
actually call** — use the companion `aihubmix` CLI (see `references/cli.md`). It
is the authenticated counterpart to the public-data commands.

- Balance / identity: `aihubmix whoami -j` (or `me -j`).
- The user's real accessible models: `aihubmix models list -j` — prefer this over
  the public `/api/v1/models` when the question is "what can *I* use" or when
  picking a model to wire into a project.
- Capability + access in one step: `candidates --capability <X> --mine` intersects
  the public candidate range with the user's callable models, so "which of these
  can *I* use" needs no manual cross-checking.
- API keys: `aihubmix keys list -j`, `keys create`, etc.
- During integration, confirm access first (`whoami` for balance, `models list`
  for a callable model), then wire and smoke-test.
- The CLI is optional and installed separately. If it is missing or the user is
  not logged in, fall back to public-data commands and point them to
  `references/cli.md` for install / `login`. Install it on the spot with
  `aihubmix_api.py install-cli` (or `--mine --auto-install`). The CLI's durable
  home is `https://github.com/AIhubmix/platfrom-cli`.
- Secrets: `keys get` and `keys token` return real key values — never print them
  in full or write them to repo files; mask like `AIHUBMIX_API_KEY`.

## Core Output Rules

- Answer the user's real task first. For integration requests, wire or show the
  integration path before model tables or contract traces.
- For standalone examples, default to two runnable formats: the current OS
  command line and JavaScript. Add Python only when the user asks, when the
  target project is Python, or when it materially helps.
- Every standalone example must include dependency install commands when
  needed, exact `AIHUBMIX_API_KEY` environment setup, runnable code or command,
  and a smoke test that prints the useful response content.
- Never paste, save, log, or echo real API keys. Use `AIHUBMIX_API_KEY` and
  prompt-based examples unless the user is explicitly managing their own
  local credential store.
- Never output prices without a price-unit line. Default to
  `USD / 1M tokens` unless `AIHUBMIX_PRICE_UNIT` is set by the team.
- Use compact token notation for people-facing output: `64K`, `200K`, `1M`.
- Avoid ambiguous phrases such as "not expanded", "not queried", "pending
  lookup", or "omitted" for fields that can be read from the source. Show the
  field, show `-` when empty, or explain the actual source/API failure.
- Query timestamps must include an explicit timezone label, for example
  `2026-06-16 10:48:51 (local time, UTC+08:00)`.
- For model-family call questions, first list matched `model_id` values, then
  give the likely default model and runnable examples. Hide pricing/context
  details unless the user asks for them.

## Protocol Coverage

The skill covers OpenAI Compatible, Anthropic Compatible, and Google
Vertex/Gemini Compatible gateway calls. The two documentation entries often
shown as:

- Anthropic Compatible / Create a Message
- Google Vertex AI Compatible / Generate Content

are supported through `example messages` and `example gemini`. See
`references/protocols-and-examples.md` before generating or wiring those calls.

## Boundaries

- Do not treat this skill as only a lookup tool. When the user wants to build,
  integrate, or call AIHubMix, provide a runnable integration path and make
  scoped code edits when the project context is available.
- Do not hardcode live model lists, prices, context lengths, provider status,
  SDK capability data, or model availability claims.
- Do not maintain a manual table of model aliases to model facts. Alias rules
  may map user wording to provider/model-family search terms only.
- Do not treat model existence in `/api/v1/models` as proof that the current
  user's key has permission to call it.
- Do not change gateway contracts or generated OpenAPI artifacts unless the
  user explicitly asks for contract development work.
- Do not over-engineer integrations. Prefer the smallest working client,
  function, route, or smoke test that proves AIHubMix is wired correctly.
- Do not assert a single model for a capability (vision, image-gen, video,
  audio, embedding…) from `/api/v1/models` metadata; its modality field is
  unreliable. Use `candidates --capability <X>` to surface a broad range and let
  the calling model choose, then confirm with `doctor`. The script picks no
  default.
- Prefer `doctor` to verify a key before wiring: it validates auth with a real
  call (the public `/v1/models` list cannot), masks keys, and redacts keys from
  upstream error bodies. Never print a full key.
