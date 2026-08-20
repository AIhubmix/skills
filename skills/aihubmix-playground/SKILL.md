---
name: aihubmix-playground
description: "Try, tune, and compare 500+ AI models on AIHubMix from a coding agent — live model discovery, four wire protocols (Chat Completions/Responses/Messages/Gemini), image/video generation, model comparison on the same prompt, and handoff links that open a preconfigured Playground (playground.aihubmix.com) in the user's browser. Use for Chinese or English requests about trying/testing a model (试用/测试模型), picking the best model for a task (选型/哪个模型好), tuning prompts or parameters (调参/温度/reasoning), comparing models on the same prompt (对比/PK), generating images or video through AIHubMix (文生图/文生视频), or sharing a configured Playground link (深链/链接直达). For integrating AIHubMix into an app or generating SDK code, prefer the aihubmixApi skill; this skill covers the try-tune-compare-handoff loop."
---

# AIHubMix Playground for Agents

You are operating AIHubMix's model-trial capabilities on behalf of a user. Everything the web Playground (https://playground.aihubmix.com/) can do, you can do through public APIs — and you can hand the user a link that opens the Playground already configured with what you set up.

Follow the steps in order. Do not report success on any step until its verification actually passed.

## Ground rules

1. **Never guess model ids, prices, or parameters from memory.** Read them from the live catalog and schemas below. Prices change; ids get delisted.
2. **HTTP 200 alone is not success.** Inspect the response body; truncated or empty content with a 200 is a failure to investigate (check `finish_reason`).
3. **Real calls cost real money.** Before running anything beyond a minimal verification call — batches, comparisons, media generation — tell the user the per-call price from the catalog and get their go-ahead.
4. **Never print the API key** into the conversation, files, or command output. Reference it as `$AIHUBMIX_API_KEY` only.

## Step 1 — Key

```bash
test -n "$AIHUBMIX_API_KEY" && echo set || echo missing
```

If missing, ask the user to create one at https://console.aihubmix.com/ and export it. Do not proceed with a placeholder.

## Step 2 — Discover models

Live catalog (no auth), with pricing and metadata:

```bash
curl -s "https://aihubmix.com/api/v1/models?type=llm&sort_by=order"
```

For any candidate model, fetch its guide — pricing, verified capabilities, endpoints, runnable example:

```
https://aihubmix.com/model/{model_id}/llms.txt
```

A guide that says "No verified integration guide" means the model is not yet covered by verification — it may still work, but confirm with a minimal real call before recommending it, and prefer covered models when several fit.

Full parameter schemas (types, ranges, enums, defaults) are linked from each guide. Filenames are content-addressed — always follow the link or `https://aihubmix.com/model-data/index.json`; never compose them by hand.

## Step 3 — Call

All four protocols run against `https://aihubmix.com`:

| Protocol | Endpoint | Auth header |
|---|---|---|
| OpenAI Chat Completions | `POST /v1/chat/completions` | `Authorization: Bearer $AIHUBMIX_API_KEY` |
| OpenAI Responses | `POST /v1/responses` | `Authorization: Bearer $AIHUBMIX_API_KEY` |
| Anthropic Messages | `POST /v1/messages` | `x-api-key: $AIHUBMIX_API_KEY` + `anthropic-version: 2023-06-01` |
| Google Gemini | `POST /gemini/v1beta/models/{model}:generateContent` | `x-goog-api-key: $AIHUBMIX_API_KEY` |

Pick the protocol matching the user's existing code. Only send parameters the model's schema declares — off-schema parameters are either rejected (400) or silently ignored.

## Step 4 — Verify end to end

```bash
curl -s https://aihubmix.com/v1/chat/completions \
  -H "Authorization: Bearer $AIHUBMIX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"<MODEL_ID>","messages":[{"role":"user","content":"Reply with exactly: AIHubMix is connected"}],"max_tokens":64}'
```

Success = body contains `AIHubMix is connected` and `model` echoes a real id. Keep `max_tokens` ≥ 64 — tighter budgets truncate the phrase on some models (`finish_reason: "length"` with a 200), which reads like a failure when the connection is fine.

## Comparing models

To compare N models on the same prompt: run the same request against each candidate (sequentially or in parallel), then report per model — output quality (quote the actual outputs), latency you measured, and cost from the catalog. Never invent a number: every figure in your comparison must come from a response you actually received or a price you actually read. Disclose total spend when done.

## Image / video generation

Media endpoints live under `/ai/v1` and each media model's llms.txt carries its real path and lifecycle:

- Images (`POST /ai/v1/images/generations`): usually synchronous — response carries output URLs.
- Video (`POST /ai/v1/videos`): asynchronous — response carries a task id; poll `GET /ai/v1/videos/{id}` until a terminal state (`completed` / `failed` / `cancelled` / `timeout`).
- Output URLs are short-lived (roughly 30 minutes) and are downloaded with the same `Authorization: Bearer` header — fetch promptly and store the content yourself.
- Media pricing is per-generation; read it from the model page before batches.

## Handing off to the human — Playground links

When the user wants to continue by hand (tweak parameters, iterate on a prompt visually), generate a link that opens the Playground preconfigured:

- Open N models at once: `https://playground.aihubmix.com/?models=<id1>,<id2>,<id3>` (up to 6, one tab per model; the Playground has no side-by-side view, so run comparisons yourself via the API and hand over tabs for the human to inspect)
- Side-by-side spec comparison: `https://aihubmix.com/compare/<id1>/<id2>` — the main site renders any two models' specs, pricing, and capabilities side by side; hand this link over when the human wants a visual spec comparison (live-output comparison is your job via the API)
- One configured session:

```
https://playground.aihubmix.com/?config=<base64url of JSON>
```

where the JSON is `{"model": "<id>", "proto": "chat|messages|responses|gemini", "params": {...}, "system": "...", "draft": "..."}` — `draft` prefills the input box without sending, so the human decides when to fire. Keep the encoded string under 6000 characters; never put keys or secrets in it. All fields except `model` are optional; unknown fields are ignored.

Give the user the link with one sentence on what it opens. The link is one-shot: parameters vanish from the address bar after loading.

## Troubleshooting

Error responses carry a `tid` (trace id) — quote it when reporting issues. Full mapping: https://docs.aihubmix.com/en/FAQs/HTTP-Codes.md

| Symptom | Likely cause | Fix |
|---|---|---|
| 401 | Missing/invalid key, or wrong auth header for the protocol | Re-check Step 1 and the header table in Step 3 |
| 403 `insufficient_user_quota` | Insufficient balance | Ask the user to top up at https://console.aihubmix.com/, then re-run Step 4 |
| 400 parameter error | Model doesn't support that parameter (most 400s pass through from the upstream provider) | Re-read the model's schema before retrying |
| 404 on model | Wrong id | Re-read the catalog; never guess ids |
| 429 | Rate limited | Back off and retry |
| 503 | No channel can serve the request, or upstream throttling | Verify the id and account access; retry later |

## More

- Site index for agents: https://aihubmix.com/llms.txt · Onboarding: https://aihubmix.com/agents.md
- Programmatic code generation: npm `@aihubmix/codegen` (4 protocols × 7 languages; the body it builds is the exact wire body the Playground sends) + `@aihubmix/model-schema`
- Gateway features needing zero client changes: model mapping & fallback, smart routing (`model: "auto"`), structured output repair — see https://docs.aihubmix.com/llms.txt
