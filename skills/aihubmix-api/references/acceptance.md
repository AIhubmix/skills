# Acceptance Checks

Use this module when validating the skill locally or explaining how to verify
that the skill works.

## Structure Validation

Run the skill creator validator from the skill folder or pass the skill path:

```bash
python <skill-creator>/scripts/quick_validate.py <path-to-aihubmix-api-skill>
```

A valid result should report that the skill is valid.

## Script Validation

Compile the helper script without creating cache files:

```bash
python -B -m py_compile scripts/aihubmix_api.py
```

## Live Source Smoke Tests

Run representative commands against live sources:

```bash
python scripts/aihubmix_api.py list --limit 5
python scripts/aihubmix_api.py report deepseek --limit 3
python scripts/aihubmix_api.py report 月之暗面最新 --limit 3
python scripts/aihubmix_api.py report 谷歌最新 --limit 3
python scripts/aihubmix_api.py report "Claude Opus 最新" --limit 3
python scripts/aihubmix_api.py report 通义千问 --limit 3
python scripts/aihubmix_api.py latest-report --limit 3
```

## Example Generation Checks

Use real model IDs from the models API when available:

```bash
python scripts/aihubmix_api.py example chat --model <live-chat-model-id>
python scripts/aihubmix_api.py example chat --model <live-chat-model-id> --lang js
python scripts/aihubmix_api.py example embeddings --model <live-embedding-model-id> --lang js
python scripts/aihubmix_api.py example images --model <live-image-model-id> --os windows --lang curl
python scripts/aihubmix_api.py example videos --model <live-video-model-id> --lang js
python scripts/aihubmix_api.py example video-content --model <live-video-model-id> --lang curl
python scripts/aihubmix_api.py example audio-speech --model <live-speech-model-id> --lang curl
python scripts/aihubmix_api.py example audio-transcriptions --model <live-transcription-model-id> --lang curl
python scripts/aihubmix_api.py example audio-translations --model <live-translation-model-id> --lang js
python scripts/aihubmix_api.py example moderations --model <live-moderation-model-id> --lang js
python scripts/aihubmix_api.py example messages --model <live-anthropic-model-id>
python scripts/aihubmix_api.py example gemini --model <live-gemini-model-id>
```

These checks confirm that Anthropic Compatible "Create a Message" and Google
Vertex/Gemini Compatible "Generate Content" are both wired into example
generation.

## SDK And Contract Checks

```bash
python scripts/aihubmix_api.py sdk-check --version 2.1.0
python scripts/aihubmix_api.py sdk-info --source npm --version 2.1.0
python scripts/aihubmix_api.py protocols
python scripts/aihubmix_api.py error-contract
python scripts/aihubmix_api.py troubleshoot --status 401 --body "{\"error\":{\"message\":\"bad key\",\"type\":\"authentication_error\"}}" --contract
```

`protocols` and `error-contract` fetch the live OpenAPI spec remotely
(`https://aihubmix.com/openapi.json`); no local checkout is used.

## Conversation-Level Acceptance

Ask realistic prompts:

- `我该怎么在 Node 项目里接入 AIHubMix 的 DeepSeek 模型`
- `aihubmix 的 gemini3.5 怎么调用`
- `给我一个 Claude/Anthropic messages 的调用示例`
- `介绍一下月之暗面最新的模型`

The response should include model ID resolution when needed, dependency setup,
`AIHUBMIX_API_KEY` setup, runnable command-line and JavaScript examples, and a
smoke test that prints useful output.
