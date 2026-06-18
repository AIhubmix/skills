# SDK

Use this module when the user asks about `@aihubmix/ai-sdk-provider`, SDK
capabilities, whether the SDK source is enough, or whether to upgrade.

## Commands

```bash
python scripts/aihubmixApi.py sdk-check --version 2.1.0
python scripts/aihubmixApi.py sdk-info --version 2.1.0
python scripts/aihubmixApi.py sdk-check --project /path/to/project --version 2.1.0
python scripts/aihubmixApi.py sdk-info --project /path/to/project --version 2.1.0
```

Use the npm registry as the remote source:
`https://registry.npmjs.org/@aihubmix%2Fai-sdk-provider`.

## What The SDK Source Is For

Use the SDK package for:

- JavaScript SDK usage examples.
- Provider factory names and imports.
- AI SDK feature surface.
- Default environment variable, base URL, and header behavior.
- Installed/latest version checks.

Do not use the SDK package as the source for live model price, context,
availability, or model list. Those belong to
`https://aihubmix.com/api/v1/models`.

## Version Policy

- Report installed version, target version, npm latest version, and source.
- Always state `Auto update: not performed`.
- Do not run `npm install`, `npm update`, or package-manager writes unless the
  user explicitly confirms the target project and version.
- If a newer version exists, say to review the changelog before updating.
- Do not imply every query should update the SDK.

## Capability Output

Use `sdk-info` to report the provider capability surface, including:

- chat
- responses
- embedding
- image
- transcription
- speech
- tools
- `AIHUBMIX_API_KEY`
- base URL
- header/routing defaults

Existing sources are sufficient for SDK capability output because the package
exposes these methods and defaults in its package type declarations and built
output. Treat `sdk-info` as SDK usage metadata. Do not keep a bundled SDK
capability baseline.

## Preferred JS Text Example

For default chat/text examples, prefer this SDK path:

```js
import { aihubmix } from "@aihubmix/ai-sdk-provider";
import { generateText } from "ai";

const { text } = await generateText({
  model: aihubmix(process.env.AIHUBMIX_MODEL ?? "model-id"),
  prompt: "Say hello in one short sentence.",
});

console.log(text);
```

For non-chat protocols or protocols not covered by the SDK surface, use direct
`fetch` examples from `references/protocols-and-examples.md`.
