# AIHubMix API Troubleshooting

Use this reference only when the user asks to debug an AIHubMix API call,
HTTP status, error body, endpoint mismatch, model availability issue, or
OpenAI-compatible invocation problem.

## Required Evidence

Collect these before drawing conclusions:

- Endpoint path and method.
- Model ID exactly as sent.
- HTTP status.
- JSON error body.
- `X-Request-Id` response header when available.
- Whether the request used OpenAI, Anthropic, or Gemini protocol shape.

## Gateway Error Shape

`AIhubmix/aihubmix-openapi` defines a unified `GatewayError` envelope for 4XX
and 5XX responses:

```json
{
  "error": {
    "message": "Human-readable error message",
    "type": "invalid_request_error",
    "param": "model",
    "code": "some_code"
  }
}
```

`request_id` is expected in the `X-Request-Id` response header, not in the body.

## First Checks

- `401` or `403`: confirm the API key exists and the endpoint uses the correct auth header.
- `404`: confirm endpoint path and model ID against `aihubmix-openapi` and `/api/v1/models`.
- `400`: validate the request body against `openapi.json` or `contract.json`; check unsupported fields, endpoint mismatch, context length, and max output.
- `429`: check rate limits, quota, and retry policy.
- `5XX`: preserve status, body, and request ID; treat as gateway or upstream failure.

## Auth Matrix

- OpenAI-shaped endpoints such as `/v1/chat/completions` and `/v1/responses`: `Authorization: Bearer $AIHUBMIX_API_KEY`.
- Anthropic-shaped `/v1/messages`: `x-api-key: $AIHUBMIX_API_KEY`; Bearer is a compatibility fallback.
- Gemini-shaped `/gemini/v1beta/...`: `x-goog-api-key: $AIHUBMIX_API_KEY` or `?key=`.

## Useful Commands

```bash
python scripts/aihubmixApi.py protocols
python scripts/aihubmixApi.py get <model-id>
python scripts/aihubmixApi.py troubleshoot --status 400 --body-file error.json --endpoint /v1/chat/completions --model <model-id>
```
