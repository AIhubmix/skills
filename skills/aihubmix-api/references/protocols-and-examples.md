# Protocols And Examples

Use this module for endpoint selection, Anthropic Compatible calls, Google
Vertex/Gemini Compatible calls, OpenAI-compatible calls, and runnable example
generation.

## Endpoint Matrix

Treat these gateway endpoints as available integration targets. Use
`protocols` or the OpenAPI contract to verify request schemas when
implementing project code, especially for multipart and binary responses.

| Capability | Helper protocol | Method | Endpoint | Auth |
|---|---|---:|---|---|
| Chat completion | `chat` | POST | `/v1/chat/completions` | Bearer |
| Model response | `responses` | POST | `/v1/responses` | Bearer |
| Legacy completion | `completions` | POST | `/v1/completions` | Bearer |
| Embedding | `embeddings` | POST | `/v1/embeddings` | Bearer |
| Image generation | `images` | POST | `/v1/images/generations` | Bearer |
| Video creation | `videos` | POST | `/v1/videos` | Bearer |
| Video retrieval | `video-retrieve` | GET | `/v1/videos/{video_id}` | Bearer |
| Video deletion | `video-delete` | DELETE | `/v1/videos/{video_id}` | Bearer |
| Video content download | `video-content` | GET | `/v1/videos/{video_id}/content` | Bearer |
| Video remix | `video-remix` | POST | `/v1/videos/{video_id}/remix` | Bearer |
| Speech synthesis | `audio-speech` | POST | `/v1/audio/speech` | Bearer |
| Audio transcription | `audio-transcriptions` | POST | `/v1/audio/transcriptions` | Bearer, multipart |
| Audio translation | `audio-translations` | POST | `/v1/audio/translations` | Bearer, multipart |
| Moderation | `moderations` | POST | `/v1/moderations` | Bearer |
| Anthropic message | `messages` | POST | `/v1/messages` | `x-api-key` preferred |
| Gemini generateContent | `gemini` | POST | `/gemini/v1beta/models/{model}:generateContent` | `x-goog-api-key` |

The documentation entries "Anthropic Compatible / Create a Message" and
"Google Vertex AI Compatible / Generate Content" are covered by:

```bash
python scripts/aihubmix_api.py example messages --model <claude-or-anthropic-model-id>
python scripts/aihubmix_api.py example gemini --model <gemini-model-id>
```

## Protocol Selection

Choose the endpoint shape internally. Do not show a separate endpoint/auth
explanation block unless the user asks for protocol details or troubleshooting.

- `gemini_api` -> Gemini native `generateContent`.
- `claude_api` -> Claude/Anthropic-compatible `/v1/messages`.
- `responses` -> OpenAI Responses.
- `chat_completions` or plain text `llm` -> OpenAI-compatible chat.
- Image tasks -> `/v1/images/generations`.
- Video tasks -> `/v1/videos` first, then retrieve/download/remix/delete when
  lifecycle management is needed.
- Audio output -> `/v1/audio/speech`, write binary output to a file.
- Audio input -> `/v1/audio/transcriptions` or `/v1/audio/translations` with
  multipart upload.
- Embeddings and moderation -> dedicated endpoints, return structured results
  instead of chat text.

If a model's endpoint field is empty:

- For plain `llm`, say `not declared; use OpenAI-compatible chat example by
  default`.
- For image/video/audio or mixed-type models, say `not declared; choose
  endpoint by model type and verify against contract`.

## Example Commands

```bash
python scripts/aihubmix_api.py example chat --model <model-id>
python scripts/aihubmix_api.py example responses --model <model-id> --lang json
python scripts/aihubmix_api.py example embeddings --model <model-id>
python scripts/aihubmix_api.py example images --model <model-id>
python scripts/aihubmix_api.py example videos --model <model-id>
python scripts/aihubmix_api.py example video-retrieve --model <model-id>
python scripts/aihubmix_api.py example video-delete --model <model-id>
python scripts/aihubmix_api.py example video-content --model <model-id>
python scripts/aihubmix_api.py example video-remix --model <model-id>
python scripts/aihubmix_api.py example audio-speech --model <model-id>
python scripts/aihubmix_api.py example audio-transcriptions --model <model-id>
python scripts/aihubmix_api.py example audio-translations --model <model-id>
python scripts/aihubmix_api.py example moderations --model <model-id>
python scripts/aihubmix_api.py example messages --model <model-id>
python scripts/aihubmix_api.py example gemini --model <model-id>
```

## Standalone Example Output

Default standalone examples must contain two formats:

1. Current OS command line:
   - Auto-detect the current OS.
   - On Windows, output PowerShell.
   - On macOS/Linux, output shell `curl`.
   - Prompt for `AIHUBMIX_API_KEY` instead of embedding a real key.
   - Print the useful response content directly.
   - On Windows, set UTF-8 before the request:
     `$OutputEncoding = [System.Text.Encoding]::UTF8`,
     `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`, and
     `[Console]::InputEncoding = [System.Text.Encoding]::UTF8`.
   - On Windows chat examples, assign `Invoke-RestMethod` to `$response` and
     print `$response.choices[0].message.content` with
     `[Console]::WriteLine(...)`.
   - On macOS/Linux chat examples, pipe JSON through a standard-library parser
     such as `python3 -c` to print `choices[0].message.content`.
2. JavaScript:
   - For default chat/text examples, prefer:
     `npm install @aihubmix/ai-sdk-provider ai`.
   - Import `aihubmix` from `@aihubmix/ai-sdk-provider` and `generateText`
     from `ai`.
   - For non-OpenAI-shaped protocols, use `fetch` with the correct endpoint
     and auth header.
   - Print the main result directly, such as `console.log(text)`.

Add Python only when the user asks, when the project is Python, or when the
requested integration naturally uses the OpenAI Python client. For Python
OpenAI-compatible chat, use `base_url="https://aihubmix.com/v1"` and
`api_key=os.environ["AIHUBMIX_API_KEY"]`.

## Setup Commands

Include the exact environment setup command before code that depends on a key:

```powershell
$env:AIHUBMIX_API_KEY = Read-Host "Paste AIHubMix API Key"
```

```bash
export AIHUBMIX_API_KEY="sk-..."
```

Include dependency installation commands when a library is used:

```bash
npm install @aihubmix/ai-sdk-provider ai
pip install openai
```

## Writing Style

- Before every code block, write one short connective sentence explaining who
  should use the example and what it does.
- Do not jump from a heading like `Windows PowerShell` directly into code.
- Do not expose raw endpoint tokens as the only explanation. Map common values:
  - `chat_completions` -> `OpenAI-compatible chat`
  - `gemini_api` -> `Gemini native`
  - `claude_api` -> `Claude/Anthropic-compatible`
- For call-intent questions, put URL and auth headers inside runnable examples
  where they are needed, not as a detached protocol block.
- For test commands, never leave users with only folded response objects such
  as PowerShell's `choices : {@{...}}`; print the primary content field.
