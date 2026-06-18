# Integration Workflow

Use this module when the user asks how to access, integrate, wire, or build
with AIHubMix in a project.

## Goal

Optimize for a working implementation, not a documentation summary. If project
files are available, inspect and edit the project. If no project exists,
generate a minimal runnable example for the user's OS and preferred language.

## Steps

1. Inspect the project:
   - Detect language/framework from `package.json`, `requirements.txt`,
     `pyproject.toml`, route files, server entrypoints, and existing AI SDK or
     OpenAI client usage.
   - Reuse existing conventions for env loading, API routes, service modules,
     error handling, logging, and tests.
2. Choose the integration path:
   - JavaScript/TypeScript text generation: prefer
     `@aihubmix/ai-sdk-provider` with the Vercel AI SDK when it fits the
     project.
   - Existing OpenAI-compatible Python or OpenAI client projects: use
     `base_url="https://aihubmix.com/v1"` and `AIHUBMIX_API_KEY`.
   - Direct protocol access: choose the endpoint from
     `references/protocols-and-examples.md`.
   - Embeddings, image, audio, video, or moderation tasks: use the matching
     endpoint. Do not force a chat example for non-chat capabilities.
3. Resolve the model ID dynamically:
   - Use `/api/v1/models` through `report <query>` for aliases such as
     `deepseek`, `gemini3.5`, `月之暗面`, or `Claude Opus 最新`.
   - If the user is logged into the `aihubmix` CLI, prefer
     `aihubmix models list -j` to pick a model their token can ACTUALLY call,
     and `aihubmix whoami` to confirm balance before testing (see
     `references/cli.md`). The public list is the full catalog and may include
     models the user's key cannot access.
   - Keep the model configurable with an environment variable or a simple
     constant that is easy to replace.
   - Do not hardcode provider availability, price, or context in project code.
4. Add integration artifacts:
   - Add a small client wrapper, route handler, command, or example file that
     matches the project's style.
   - Include dependency install commands, but do not run package-manager writes
     unless the user asked Codex to modify the project and the package manager
     is clear.
   - Include exact environment variable setup commands and `.env.example`
     placeholders when editing a project. Never write real API keys to files.
5. Verify:
   - Provide one smoke test that prints useful model output.
   - If tests or type checks exist, run the narrow relevant command after code
     changes.
   - If a live API call cannot run because no key is available, say static
     validation passed and give the exact command the user can run locally.

## Answer Shape

For integration answers, start with the practical wiring:

```text
接入方案
- 使用的模型/协议/SDK
- 需要设置的环境变量
- 需要安装的依赖

代码或命令
<project edits, runnable command-line smoke test, JavaScript/Python code>

验证方式
<how to run and what output to expect>
```

When editing a project, prioritize code changes over generic example output.
Summarize changed files, the endpoint/capability wired into the app, and the
exact verification commands that were run or can be run.

For project integration, do not dump every generic example unless the user asks
for standalone samples. Installation commands, environment variables, and smoke
tests should appear as project-specific setup or validation notes.

## Minimal Project Patterns

Use the smallest useful artifact:

- `src/lib/aihubmix.ts` or `lib/aihubmix.ts` for a reusable JS/TS client.
- `src/app/api/.../route.ts` or existing backend route conventions for Next.js.
- `scripts/aihubmix-smoke.mjs` for a command-line smoke test in JS projects.
- `aihubmix_client.py` or a focused service module for Python projects.

Do not introduce a new framework, app structure, or broad refactor unless the
user asks.

## Security

- Read keys from `AIHUBMIX_API_KEY`.
- Add `.env.example` with `AIHUBMIX_API_KEY=sk-...` placeholder only.
- Do not write real user-provided keys into repo files.
- Do not print full keys in final answers or logs.
