# AIHubMix CLI (account / auth — authenticated companion)

The public models API (`/api/v1/models`) lists ALL models and prices but knows
nothing account-specific. The official **`aihubmix` CLI** fills that gap: it
returns the **current user's** balance, API keys, and the models **their token
can actually call**. Use it for any account / balance / key / "what can *I*
access" question, and to ground integration in what the user really has.

`aihubmix` is a separate companion binary, not bundled with this skill. The
skill's `scripts/aihubmixApi.py` covers public catalog/contract data; the
`aihubmix` CLI covers authenticated account data. They are complementary.

## Install

**Canonical home (always current — this is the durable anchor):**
https://github.com/AIhubmix/platfrom-cli — even if an install URL ever moves, the
current method is always findable there.

Official per-OS installer (the executable entrypoints):

```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/AIhubmix/platfrom-cli/main/install.ps1 | iex
```
```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/AIhubmix/platfrom-cli/main/install.sh | sh
```

Or let this skill install it (auto-detects your OS and runs the official
installer above):

```bash
python scripts/aihubmixApi.py install-cli
```

Installs to `%LOCALAPPDATA%\aihubmix\bin` (Windows) or `~/.local/bin` /
`/usr/local/bin` (unix) and adds it to PATH. If `aihubmix` is not yet on PATH
(fresh install / current shell), call it by full path, e.g. on Windows
`%LOCALAPPDATA%\aihubmix\bin\aihubmix.exe`.

## Authenticate

```bash
aihubmix login      # paste a Manage Key (not echoed); saved to ~/.aihubmix/config.json (0600)
aihubmix logout     # clear local credentials
```

Credential priority: `--token <ManageKey>` > `AIHUBMIX_TOKEN` env >
`~/.aihubmix/config.json`. For CI / non-interactive use, pass `--token` or set
`AIHUBMIX_TOKEN`. Note: the Manage Key is NOT the same as the `AIHUBMIX_API_KEY`
used for inference calls.

## Commands (add `-j` / `--json` for machine-readable output)

```bash
aihubmix whoami            # current identity + balance   (alias: status)
aihubmix me                # current user info + balance   (alias: account)
aihubmix models list       # models the CURRENT token can actually call
aihubmix keys list         # the user's API keys
aihubmix keys get <id>     # one key's details — INCLUDES the secret key value
aihubmix keys search <kw>  # search keys by keyword
aihubmix keys create | update | delete ...   # manage keys
aihubmix keys token        # the current user's token
```

## Platform API ↔ command map

The CLI wraps the AIHubMix **Platform API**. Endpoint → command:

| Platform API endpoint | CLI command |
|---|---|
| Model Management API (GET) | `aihubmix models list` |
| Current User Info (GET) | `aihubmix me` (or `whoami`) |
| Get KEY List (GET) | `aihubmix keys list` |
| Create New KEY (POST) | `aihubmix keys create` |
| Update KEY (PUT) | `aihubmix keys update <id>` |
| Retrieve Single KEY Details (GET) | `aihubmix keys get <id>` |
| Delete KEY (DEL) | `aihubmix keys delete <id> [--yes]` |
| Search KEY (GET) | `aihubmix keys search <keyword>` |
| Obtain User KEY (GET) | `aihubmix keys token` |
| Available Models (GET) | `aihubmix models list` |

## When to use it

- "我的余额 / how much credit do I have?" → `aihubmix whoami -j` (or `me -j`).
- "我能用哪些模型 / which models can I actually call?" → `aihubmix models list -j`.
  This is the user's REAL access list. The public `/api/v1/models` is the full
  catalog and does NOT reflect per-key permission, so prefer this for "what *I*
  can use" and for picking a model during integration.
- "which of these candidates can *I* use?" → `aihubmixApi.py candidates
  --capability <X> --mine` intersects the public candidate range with this list
  automatically (add `--auto-install` to install the CLI if missing).
- "我的 key / 列出或新建我的 API Key" → `aihubmix keys list -j`, `keys create`.
- During project integration: confirm access first — `aihubmix whoami` (is there
  balance?) and `aihubmix models list` (pick a model the user can actually call,
  instead of guessing from the public catalog). Then wire and smoke-test.

## Safety

- `aihubmix keys get` and `aihubmix keys token` return real secret values. Treat
  them like `AIHUBMIX_API_KEY`: never print them in full, never write them into
  repo files or logs, mask in any output. Prefer referencing keys by id / name.
- When wiring a project, prefer reading the key from the user's environment
  (`AIHUBMIX_API_KEY`) over fetching a secret via the CLI.
- If `aihubmix` is not installed or the user is not logged in, fall back to this
  skill's public-data commands and tell the user how to install / `login`.
