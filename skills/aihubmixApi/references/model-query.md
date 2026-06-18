# Model Query

Use this module for model list, model-family introduction, latest models,
single-model detail, price/context comparison, and model ID selection.

## Commands

Run from the skill directory:

```bash
python scripts/aihubmixApi.py list --limit 50
python scripts/aihubmixApi.py report <query> --limit 5
python scripts/aihubmixApi.py latest-report --limit 5
python scripts/aihubmixApi.py get <model-id>
python scripts/aihubmixApi.py compare <model-a> <model-b> <model-c>
```

Use `--source` only for caller-provided one-off debugging. Default to
`https://aihubmix.com/api/v1/models`.

## List Models

When the user asks which models AIHubMix supports, return a compact table with:

- `model_id`
- name
- provider/developer
- context
- max output
- type/endpoint

If the user asks for a category, use `report <query>` or filter the JSON output
instead of inventing a static provider list.

## Family Or Alias Query

Use `report <query>` for natural-language aliases and provider nicknames such
as:

- `qwen3.5`, `通义`, `千问`
- `gpt5.4`, `OpenAI`, `ChatGPT`
- `opus4.8`, `Claude Opus 最新`, `Anthropic`
- `gemini3.5`, `谷歌最新`, `Google`, `Gemini`
- `月之暗面最新`, `Kimi`, `Moonshot`
- `deepseek`, `深度求索`
- `豆包`, `智谱`, `GLM`

Alias normalization only affects search terms and relevance ranking. Never use
alias rules as the source for price, context, availability, or protocol facts.
Those fields must still come from `/api/v1/models`.

For model-family or alias reports, include the helper's `Normalized query
terms` line so users can see how nicknames were resolved.

## Latest Models

When the user asks for latest models with price/context/example:

```bash
python scripts/aihubmixApi.py latest-report --limit 5
```

Use the report output directly unless the user asks for a different format.
The helper must preserve the original order returned by `/api/v1/models`; do
not sort by model ID before selecting the first N rows.

The report must include:

- Data source.
- Query time with explicit timezone label, such as
  `2026-06-16 10:48:51 (local time, UTC+08:00)`.
- Latest definition, usually source order from `/api/v1/models` unless the API
  exposes created/updated fields.
- Price unit, defaulting to `USD / 1M tokens`.
- Pricing values, context, max output, notes, and examples.

## Single Model

When the user provides a model ID or asks about one model:

```bash
python scripts/aihubmixApi.py get <model-id>
```

Return model ID, display name, provider/developer, context, max output,
pricing, type/endpoints, and features/modalities. If the model is not found,
say it was not found in the selected model source. Do not guess nearby IDs as
facts.

## Compare Models

When comparing price, context, max output, or capability:

```bash
python scripts/aihubmixApi.py compare <model-a> <model-b> ...
```

Compare only fields returned by the model API. Always show the price unit.
Make recommendations only after separating facts from assumptions. Rank prices
only when the returned price fields are directly comparable.

## Output Rules

- Start with a short user-facing answer, then show raw fields.
- Never output prices without `Price unit: USD / 1M tokens` or the configured
  override.
- Display pricing object keys exactly as returned, such as `input`, `output`,
  `cache_read`, and `cache_write`.
- Use compact token notation in prose and tables: `64K`, `200K`, `991K`, `1M`.
- If a structured field is `0` or empty, show it as returned and add a note
  only when model description or source data explains it.
- Do not use ambiguous phrases such as "not expanded", "not queried",
  "pending lookup", "omitted", or "etc." for source-readable fields.
- If a lookup fails, state which source failed and what the failure was.
- Data sources shown to users must be remote URLs, not local files.

## Call-Intent Query

For requests like "怎么调用 gemini3.5", "我该怎么接入 deepseek",
"给我 opus4.6 示例", or "API example":

1. Resolve matching model IDs with `report <query>`.
2. List only matched `model_id` values first.
3. Pick the likely default model ID to copy.
4. Generate runnable examples using `references/protocols-and-examples.md`.
5. Do not include pricing, context, max output, developer IDs, raw endpoint
   tokens, features, or trace details unless the user asks.

When showing multiple optional model IDs, add one sentence: users can call a
different model by replacing the `model` or `model_id` value in the examples.

## Capability Discovery (vision / image-gen / video / audio / embedding …)

For "which model can do X" requests (X = 图片输入/看图, 文生图, 文生视频,
语音合成/识别, 向量, 重排 …), do NOT decide a single model from the
`/api/v1/models` modality field — it is unreliable (some capable models lack the
tag; some incapable ones carry it).

```bash
python scripts/aihubmixApi.py candidates --capability vision     --limit 40
python scripts/aihubmixApi.py candidates --capability image-gen
python scripts/aihubmixApi.py candidates --capability video
python scripts/aihubmixApi.py candidates --capability audio-tts
python scripts/aihubmixApi.py candidates --capability audio-stt
python scripts/aihubmixApi.py candidates --capability embedding
python scripts/aihubmixApi.py candidates --capability rerank
```

Aliases are accepted (e.g. `多模态`/`mm` → vision, `t2i`/`生图` → image-gen,
`tts` → audio-tts). `vision-candidates` is shorthand for
`candidates --capability vision`.

`candidates` returns a broad range scored by three signals shown in the `signal`
column — `protocol` (endpoint type), `family` (known model-family name),
`modality` (metadata keyword) — with protocol/family treated as reliable and
modality-only as noisy. For input-modality capabilities (vision) it filters out
non-chat models. It deliberately picks no default: present or reason over the
range, let the calling model pick what fits the task and budget, then confirm the
choice actually works:

```bash
python scripts/aihubmixApi.py doctor --model <model-id> --image   # vision probe
```

### Filter to what the user can actually call (`--mine`)

Add `--mine` to intersect the candidate range with the models the user's token
can really call (via `aihubmix models list`), so selection isn't a guess:

```bash
python scripts/aihubmixApi.py candidates --capability vision --mine
python scripts/aihubmixApi.py candidates --capability image-gen --mine --auto-install
```

`--mine` needs the companion `aihubmix` CLI + login (`references/cli.md`). If the
CLI is missing it errors with how to install (or add `--auto-install` to install
it on the spot); if not logged in it points to `aihubmix login`. Without `--mine`
the command is unchanged and has no CLI dependency.

## Preflight A Key

Before wiring a key into a project, or when debugging `401`/auth problems, run:

```bash
AIHUBMIX_API_KEY=<key> python scripts/aihubmixApi.py doctor --model <id> --image
```

It validates auth with a real minimal call (the public `/v1/models` list does
not require auth, so it cannot validate a key), optionally smoke-tests text and
image input, prints a `✓/✗` checklist, exits non-zero on failure, masks the
key, and redacts keys from upstream error bodies.
