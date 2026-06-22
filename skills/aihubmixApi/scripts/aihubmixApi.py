#!/usr/bin/env python3
"""
Small AIHubMix API helper for Codex skills.

The script intentionally keeps volatile model data out of the skill. It reads
model metadata from the live models API by default, or from a caller-provided
JSON file for local validation.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# Force UTF-8 stdout/stderr so Chinese output is not mangled to GBK mojibake
# on Windows or when the stream is redirected/piped (default code page there
# is cp936, not UTF-8).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # non-reconfigurable stream
        pass


# Output language for status lines/labels: "en" (default, neutral) or "zh".
# Set via the global --lang flag or AIHUBMIX_LANG; main() resolves it into _LANG.
_LANG = (os.environ.get("AIHUBMIX_LANG") or "en").strip().lower()
if _LANG not in ("en", "zh"):
    _LANG = "en"


def _t(en: str, zh: str) -> str:
    """Pick output text by the resolved language (data values are never translated)."""
    return zh if _LANG == "zh" else en


DEFAULT_MODELS_URL = "https://aihubmix.com/api/v1/models"
DEFAULT_SERVER_URL = "https://aihubmix.com"
DEFAULT_PRICE_UNIT = "USD / 1M tokens"
SDK_PACKAGE_NAME = "@aihubmix/ai-sdk-provider"
SDK_RECOMMENDED_VERSION = "2.1.0"
SDK_REGISTRY_URL = "https://registry.npmjs.org/@aihubmix%2Fai-sdk-provider"
OPENAPI_REPO_URL = "https://github.com/AIhubmix/aihubmix-openapi"
OPENAPI_JSON_URL = "https://aihubmix.com/openapi.json"
CONTRACT_JSON_URL = "https://aihubmix.com/contract.json"
GATEWAY_ERRORS_URL = "https://github.com/AIhubmix/aihubmix-openapi/blob/main/gateway/errors.yml"

# Companion `aihubmix` CLI. The repo URL is the durable anchor shown everywhere
# (stable even if the install scripts move); the raw install scripts are the
# per-OS executable entrypoints, derived from the same repo path so there is a
# single source of truth and the CLI can always be re-found.
CLI_BIN = "aihubmix"
CLI_REPO = "AIhubmix/platfrom-cli"
CLI_REPO_URL = f"https://github.com/{CLI_REPO}"
CLI_RAW_BASE = f"https://raw.githubusercontent.com/{CLI_REPO}/main"
CLI_INSTALL_PS1 = f"{CLI_RAW_BASE}/install.ps1"
CLI_INSTALL_SH = f"{CLI_RAW_BASE}/install.sh"

PROTOCOL_ALIASES = {
    "chat": "chat",
    "chat-completions": "chat",
    "model-response": "responses",
    "model-responses": "responses",
    "response": "responses",
    "completion": "completions",
    "embedding": "embeddings",
    "image": "images",
    "image-generation": "images",
    "video": "videos",
    "retrieve-video": "video-retrieve",
    "download-video": "video-content",
    "video-download": "video-content",
    "remix-video": "video-remix",
    "speech": "audio-speech",
    "tts": "audio-speech",
    "transcription": "audio-transcriptions",
    "translation": "audio-translations",
    "moderation": "moderations",
    "message": "messages",
    "anthropic": "messages",
    "generate-content": "gemini",
    "vertex": "gemini",
    "google": "gemini",
}

PROTOCOL_SPECS: dict[str, dict[str, Any]] = {
    "chat": {
        "label": "OpenAI-Compatible Chat",
        "method": "POST",
        "path": "/v1/chat/completions",
        "family": "openai",
    },
    "responses": {
        "label": "OpenAI Model Responses",
        "method": "POST",
        "path": "/v1/responses",
        "family": "openai",
    },
    "completions": {
        "label": "OpenAI-Compatible Legacy Completion",
        "method": "POST",
        "path": "/v1/completions",
        "family": "openai",
    },
    "embeddings": {
        "label": "OpenAI-Compatible Embeddings",
        "method": "POST",
        "path": "/v1/embeddings",
        "family": "openai",
    },
    "images": {
        "label": "OpenAI-Compatible Image Generation",
        "method": "POST",
        "path": "/v1/images/generations",
        "family": "openai",
    },
    "videos": {
        "label": "OpenAI-Compatible Video Creation",
        "method": "POST",
        "path": "/v1/videos",
        "family": "openai",
    },
    "video-retrieve": {
        "label": "OpenAI-Compatible Video Retrieval",
        "method": "GET",
        "path": "/v1/videos/{video_id}",
        "family": "openai",
        "needs_video_id": True,
    },
    "video-delete": {
        "label": "OpenAI-Compatible Video Deletion",
        "method": "DELETE",
        "path": "/v1/videos/{video_id}",
        "family": "openai",
        "needs_video_id": True,
    },
    "video-content": {
        "label": "OpenAI-Compatible Video Content Download",
        "method": "GET",
        "path": "/v1/videos/{video_id}/content",
        "family": "openai",
        "needs_video_id": True,
    },
    "video-remix": {
        "label": "OpenAI-Compatible Video Remix",
        "method": "POST",
        "path": "/v1/videos/{video_id}/remix",
        "family": "openai",
        "needs_video_id": True,
    },
    "audio-speech": {
        "label": "OpenAI-Compatible Speech",
        "method": "POST",
        "path": "/v1/audio/speech",
        "family": "openai",
        "binary_response": True,
    },
    "audio-transcriptions": {
        "label": "OpenAI-Compatible Audio Transcription",
        "method": "POST",
        "path": "/v1/audio/transcriptions",
        "family": "openai",
        "multipart": True,
    },
    "audio-translations": {
        "label": "OpenAI-Compatible Audio Translation",
        "method": "POST",
        "path": "/v1/audio/translations",
        "family": "openai",
        "multipart": True,
    },
    "moderations": {
        "label": "OpenAI-Compatible Moderation",
        "method": "POST",
        "path": "/v1/moderations",
        "family": "openai",
    },
    "messages": {
        "label": "Claude/Anthropic-Compatible Messages",
        "method": "POST",
        "path": "/v1/messages",
        "family": "anthropic",
    },
    "gemini": {
        "label": "Google Vertex/Gemini-Compatible Generate Content",
        "method": "POST",
        "path": "/gemini/v1beta/models/{model}:generateContent",
        "family": "gemini",
    },
}


def display_models_source() -> str:
    return DEFAULT_MODELS_URL


def display_openapi_source(filename: str = "openapi.json") -> str:
    if filename == "openapi.json":
        return OPENAPI_JSON_URL
    if filename == "contract.json":
        return CONTRACT_JSON_URL
    return OPENAPI_REPO_URL


def display_error_contract_source() -> str:
    return OPENAPI_JSON_URL


def load_json_source(source: str | None) -> Any:
    # Always fetch live (no caching): every lookup hits the source directly.
    source = source or os.environ.get("AIHUBMIX_MODELS_URL") or DEFAULT_MODELS_URL
    if source == "-":
        return json.load(sys.stdin)
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(
            source,
            headers={
                "Accept": "application/json",
                "User-Agent": "aihubmixApi-skill/0.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"HTTP {exc.code} while fetching {source}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"Could not fetch {source}: {exc.reason}") from exc

    path = Path(source).expanduser()
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_models(payload: Any) -> list[dict[str, Any]]:
    return sorted(extract_models_in_source_order(payload), key=lambda item: model_id(item).lower())


def extract_models_in_source_order(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        candidates = None
        for key in ("data", "models", "items", "list", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates = value
                break
            if isinstance(value, dict):
                nested = extract_models_in_source_order(value)
                if nested:
                    candidates = nested
                    break
        if candidates is None:
            candidates = [payload] if any(k in payload for k in ("id", "model", "model_id")) else []
    else:
        candidates = []

    return [item for item in candidates if isinstance(item, dict)]


def model_id(model: dict[str, Any]) -> str:
    for key in ("model_id", "id", "model", "name", "slug"):
        value = model.get(key)
        if value is not None:
            return str(value)
    return ""


def model_label(model: dict[str, Any]) -> str:
    for key in ("model_name", "name", "display_name", "label", "title"):
        value = model.get(key)
        if value:
            return str(value)
    return model_id(model)


def developer(model: dict[str, Any]) -> str:
    for key in ("developer", "provider", "developer_id", "provider_id", "owned_by"):
        value = model.get(key)
        if value:
            return str(value)
    return "-"


def context_length(model: dict[str, Any]) -> str:
    for key in (
        "context_length",
        "context_window",
        "max_context",
        "max_context_length",
        "input_context_length",
    ):
        value = model.get(key)
        if value is not None:
            return str(value)
    return "-"


def max_output(model: dict[str, Any]) -> str:
    for key in ("max_output", "max_output_tokens", "output_context_length"):
        value = model.get(key)
        if value is not None:
            return str(value)
    return "-"


def format_tokens(value: str) -> str:
    if value in {"", "-"}:
        return "-"
    try:
        number = int(float(value))
    except ValueError:
        return value
    if number == 0:
        return "0"
    if number >= 1_000_000 and number % 1_000_000 == 0:
        return f"{number // 1_000_000}M"
    if number >= 1_000_000:
        compact_value = number / 1_000_000
        return f"{compact_value:.2f}".rstrip("0").rstrip(".") + "M"
    if number >= 1_000 and number % 1_000 == 0:
        return f"{number // 1_000}K"
    if number >= 1_000:
        compact_value = number / 1_000
        return f"{compact_value:.1f}".rstrip("0").rstrip(".") + "K"
    return str(number)


def context_display(model: dict[str, Any]) -> str:
    return format_tokens(context_length(model))


def max_output_display(model: dict[str, Any]) -> str:
    return format_tokens(max_output(model))


def compact(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return ",".join(compact(item) for item in value[:8]) or "-"
    if isinstance(value, dict):
        parts = []
        for key in sorted(value):
            item = value[key]
            if item is not None:
                parts.append(f"{key}={compact(item)}")
        return "; ".join(parts) or "-"
    return str(value)


def pricing(model: dict[str, Any]) -> str:
    value = model.get("pricing") or model.get("price") or model.get("prices")
    return compact(value)


def price_unit() -> str:
    return os.environ.get("AIHUBMIX_PRICE_UNIT", DEFAULT_PRICE_UNIT)


def query_time_label() -> str:
    now = datetime.now().astimezone()
    offset = now.strftime("%z")
    if offset:
        offset_label = f"UTC{offset[:3]}:{offset[3:]}"
    else:
        offset_label = "local timezone"
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    return _t(f"{stamp} (local time, {offset_label})", f"{stamp} (本地时间，{offset_label})")


def types(model: dict[str, Any]) -> str:
    value = model.get("types") or model.get("type") or model.get("endpoints")
    return compact(value)


def features(model: dict[str, Any]) -> str:
    value = model.get("features") or model.get("capabilities") or model.get("input_modalities")
    return compact(value)


def endpoint_display(model: dict[str, Any]) -> str:
    raw = str(model.get("endpoints") or "").strip()
    if not raw:
        model_type = str(model.get("types") or "")
        if "llm" in model_type and "image_generation" not in model_type:
            return "not declared; use OpenAI-compatible chat example by default"
        return "not declared; choose endpoint by model type and verify against contract"
    labels = {
        "chat_completions": "OpenAI-compatible chat",
        "responses": "OpenAI Responses",
        "gemini_api": "Gemini native",
        "claude_api": "Claude/Anthropic-compatible",
        "embeddings": "Embeddings",
        "image_generation": "Image generation",
        "audio": "Audio",
        "moderations": "Moderation",
        "videos": "Video",
    }
    parts = [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]
    mapped = [labels.get(part, part) for part in parts]
    return "; ".join(mapped) if mapped else raw


def endpoint_note(model: dict[str, Any]) -> str:
    raw = str(model.get("endpoints") or "").strip()
    return raw if raw else "-"


def suggested_protocol(model: dict[str, Any]) -> str | None:
    raw_endpoint = compact(model.get("endpoints")).lower()
    raw_type = compact(model.get("types") or model.get("type")).lower()
    searchable = model_search_text(model).lower()

    if "gemini_api" in raw_endpoint:
        return "gemini"
    if "claude_api" in raw_endpoint:
        return "messages"
    if "responses" in raw_endpoint:
        return "responses"
    if "chat_completions" in raw_endpoint:
        return "chat"
    if "embedding" in raw_endpoint or "embedding" in raw_type:
        return "embeddings"
    if any(value in raw_endpoint or value in raw_type for value in ("image_generation", "image")):
        return "images"
    if any(value in raw_endpoint or value in raw_type for value in ("video", "videos")):
        return "videos"
    if any(value in raw_endpoint or value in raw_type for value in ("speech", "tts")):
        return "audio-speech"
    if "transcription" in raw_endpoint or "transcription" in raw_type:
        return "audio-transcriptions"
    if "translation" in raw_endpoint or "translation" in raw_type:
        return "audio-translations"
    if "moderation" in raw_endpoint or "moderation" in raw_type:
        return "moderations"
    if "audio" in raw_endpoint or "audio" in raw_type:
        return "audio-transcriptions"
    if "llm" in raw_type or "chat" in raw_type:
        return "chat"
    if any(value in searchable for value in ("gemini", "claude", "anthropic")):
        if "gemini" in searchable:
            return "gemini"
        return "messages"
    return "chat"


def protocol_name(protocol: str) -> str:
    protocol = normalize_protocol(protocol)
    return PROTOCOL_SPECS[protocol]["label"]


def protocol_auth_label(protocol: str) -> str:
    header_name, header_value = auth_header(protocol)
    return f"{header_name}: {header_value}"


def print_user_overview(selected: list[dict[str, Any]], query: str | None = None) -> None:
    print("## Quick Start Overview")
    print()
    if query:
        print(f"- Searched: `{query}`")
    print(f"- Models shown: `{len(selected)}`")
    print(f"- Price unit: `{price_unit()}`")
    print("- How to use: copy a `model_id`, check context/price, then run the example below.")
    print()
    print("| model_id | protocol | context | max_output | price |")
    print("|---|---|---:|---:|---|")
    for item in selected[:5]:
        protocol = suggested_protocol(item)
        protocol_label = protocol_name(protocol) if protocol else "verify endpoint by model type"
        print(
            "| "
            + " | ".join(
                [
                    f"`{model_id(item)}`",
                    protocol_label,
                    context_display(item),
                    max_output_display(item),
                    pricing(item).replace("|", "\\|"),
                ]
            )
            + " |"
        )
    print()
    print("## Technical Details")
    print()


def example_intro(kind: str, os_name: str | None = None) -> str:
    if kind == "command":
        shell_name = "Windows PowerShell" if os_name == "windows" else "macOS/Linux shell"
        return (
            f"Use this {shell_name} example when you want to test the model directly from a terminal. "
            "It asks for `AIHUBMIX_API_KEY`, sends one request, and prints the model reply."
        )
    if kind == "js":
        return (
            "Use this JavaScript example inside a Node.js project or service. "
            "Run the environment setup command below before starting the script."
        )
    if kind == "python":
        return (
            "Use this Python example for a quick backend or script test. "
            "Run the environment setup command below before starting the script."
        )
    return "Use this example as a minimal starting point."


def env_setup_block(kind: str, os_name: str | None = None) -> tuple[str, str]:
    if kind == "command":
        return "", ""
    if os_name == "windows":
        return (
            "PowerShell",
            '$env:AIHUBMIX_API_KEY = Read-Host "Paste AIHubMix API Key"',
        )
    if kind == "js":
        return (
            "bash",
            'export AIHUBMIX_API_KEY="sk-..."',
        )
    return (
        "bash",
        'export AIHUBMIX_API_KEY="sk-..."',
    )


def print_env_setup(kind: str, os_name: str | None = None) -> None:
    lang, command = env_setup_block(kind, os_name)
    if not command:
        return
    print("先设置环境变量，把 `sk-...` 换成你的 AIHubMix API Key：")
    print()
    print(f"```{lang}")
    print(command)
    print("```")
    print()


def print_model_switch_hint(selected: list[dict[str, Any]]) -> None:
    if len(selected) <= 1:
        return
    shown = ", ".join(f"`{model_id(item)}`" for item in selected[:6])
    print(f"可选模型 ID：{shown}")
    print("想切换模型时，直接把示例里的 `model` / `model_id` 换成对应 ID 即可。")
    print()


def availability_note(model: dict[str, Any]) -> str:
    desc = str(model.get("desc") or "")
    lowered = desc.lower()
    notes = []
    if "temporarily suspended" in lowered or "suspended" in lowered:
        notes.append("access note in desc")
    if "expensive" in lowered or "high price" in lowered:
        notes.append("cost note in desc")
    return ", ".join(notes) if notes else "-"


LATEST_QUERY_TERMS = ("latest", "newest", "recent", "最新", "新模型", "最近")

GENERIC_QUERY_TOKENS = {
    "aihubmix",
    "api",
    "info",
    "interface",
    "latest",
    "model",
    "models",
    "newest",
    "price",
    "pricing",
    "recent",
}

MODEL_ALIAS_GROUPS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("月之暗面", "moonshot", "kimi"), ("moonshot", "kimi")),
    (("谷歌", "google", "gemini"), ("google", "gemini")),
    (("claude", "anthropic"), ("claude", "anthropic")),
    (("opus",), ("opus",)),
    (("sonnet",), ("sonnet",)),
    (("haiku",), ("haiku",)),
    (("openai", "chatgpt", "gpt"), ("openai", "gpt")),
    (("qwen", "通义", "通义千问", "千问", "alibaba", "阿里"), ("qwen", "通义", "千问", "alibaba")),
    (("deepseek", "深度求索"), ("deepseek", "深度求索")),
    (("zhipu", "智谱", "glm"), ("zhipu", "智谱", "glm")),
    (("doubao", "豆包", "字节", "火山", "volcengine"), ("doubao", "volcengine", "字节", "火山")),
    (("minimax", "海螺"), ("minimax", "hailuo", "海螺")),
    (("零一万物", "01ai", "01-ai", "yi"), ("01-ai", "yi", "零一")),
    (("baichuan", "百川"), ("baichuan", "百川")),
    (("mistral",), ("mistral",)),
    (("llama", "meta"), ("llama", "meta")),
    (("grok", "xai", "x.ai"), ("grok", "xai", "x.ai")),
]


def normalize_search_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.lower(), flags=re.UNICODE)


def query_wants_latest(query: str) -> bool:
    lowered = query.lower()
    return any(term in lowered for term in LATEST_QUERY_TERMS)


def model_search_text(model: dict[str, Any]) -> str:
    keys = (
        "model_id",
        "id",
        "model",
        "model_name",
        "name",
        "display_name",
        "label",
        "title",
        "developer",
        "provider",
        "developer_id",
        "provider_id",
        "owned_by",
        "desc",
        "description",
        "types",
        "type",
        "endpoints",
        "features",
        "capabilities",
        "input_modalities",
    )
    return " ".join(compact(model.get(key)) for key in keys if model.get(key) is not None)


def add_query_group(
    groups: list[list[str]],
    labels: list[str],
    seen: set[tuple[str, ...]],
    label: str,
    terms: tuple[str, ...] | list[str],
) -> None:
    cleaned = tuple(dict.fromkeys(term.strip().lower() for term in terms if term.strip()))
    if not cleaned:
        return
    key = tuple(sorted(normalize_search_text(term) for term in cleaned if normalize_search_text(term)))
    if not key or key in seen:
        return
    groups.append(list(cleaned))
    labels.append(f"{label} -> {', '.join(cleaned)}" if label else ", ".join(cleaned))
    seen.add(key)


def build_query_plan(query: str) -> dict[str, Any]:
    lowered = query.lower()
    compact_query = normalize_search_text(query)
    groups: list[list[str]] = []
    labels: list[str] = []
    seen: set[tuple[str, ...]] = set()
    matched_alias_triggers: set[str] = set()

    for triggers, terms in MODEL_ALIAS_GROUPS:
        matched_trigger = None
        for trigger in triggers:
            trigger_lower = trigger.lower()
            trigger_compact = normalize_search_text(trigger)
            if trigger_lower in lowered or (trigger_compact and trigger_compact in compact_query):
                matched_trigger = trigger
                matched_alias_triggers.update(normalize_search_text(item) for item in triggers)
                break
        if matched_trigger:
            add_query_group(groups, labels, seen, matched_trigger, terms)

    for token in re.findall(r"[a-z0-9]+(?:[._-]?[a-z0-9]+)*", lowered):
        token_compact = normalize_search_text(token)
        if not token_compact or token in GENERIC_QUERY_TOKENS or token_compact in matched_alias_triggers:
            continue
        add_query_group(groups, labels, seen, token, (token,))

    if not groups and query.strip():
        add_query_group(groups, labels, seen, "raw query", (query.strip(),))

    return {
        "groups": groups,
        "labels": labels,
        "wants_latest": query_wants_latest(query),
        "compact_query": compact_query,
    }


def term_match_score(model: dict[str, Any], raw_text: str, compact_text: str, term: str) -> int:
    term_lower = term.lower()
    term_compact = normalize_search_text(term)
    model_id_lower = model_id(model).lower()
    model_id_compact = normalize_search_text(model_id(model))

    if term_lower == model_id_lower or (term_compact and term_compact == model_id_compact):
        return 100
    if term_lower and term_lower in raw_text:
        return 25
    if term_compact and term_compact in compact_text:
        return 20
    return 0


def model_query_score(model: dict[str, Any], plan: dict[str, Any]) -> int:
    raw_text = model_search_text(model).lower()
    compact_text = normalize_search_text(raw_text)
    groups = plan["groups"]
    if not groups:
        return 0

    score = 0
    for group in groups:
        group_score = max(term_match_score(model, raw_text, compact_text, term) for term in group)
        if group_score == 0:
            return 0
        score += group_score

    compact_query = plan["compact_query"]
    model_id_compact = normalize_search_text(model_id(model))
    if compact_query and compact_query == model_id_compact:
        score += 200
    elif compact_query and compact_query in model_id_compact:
        score += 80
    return score


def rank_matching_models(
    models: list[dict[str, Any]],
    query: str,
    limit: int | None = None,
    preserve_source_order: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    plan = build_query_plan(query)
    scored = [
        (index, model_query_score(item, plan), item)
        for index, item in enumerate(models)
    ]
    matches = [(index, score, item) for index, score, item in scored if score > 0]
    if preserve_source_order:
        ordered = sorted(matches, key=lambda row: row[0])
    else:
        ordered = sorted(matches, key=lambda row: (-row[1], model_id(row[2]).lower()))
    selected = [item for _, _, item in ordered]
    if limit is not None:
        selected = selected[:limit]
    return selected, plan


def find_model(models: list[dict[str, Any]], target: str) -> dict[str, Any] | None:
    selected, _ = rank_matching_models(models, target, limit=1)
    return selected[0] if selected else None


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    print(" | ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)))


def cmd_list(args: argparse.Namespace) -> None:
    models = extract_models(load_json_source(args.source))
    if args.query:
        models, _ = rank_matching_models(models, args.query)
    if args.json:
        print(json.dumps(models[: args.limit], ensure_ascii=False, indent=2))
        return
    rows = []
    for item in models[: args.limit]:
        rows.append(
            [
                model_id(item),
                model_label(item),
                developer(item),
                context_display(item),
                max_output_display(item),
                types(item),
            ]
        )
    print_table(["model_id", "name", "provider", "context", "max_output", "types"], rows)
    print(f"\nsource: {display_models_source()}")


def cmd_get(args: argparse.Namespace) -> None:
    models = extract_models(load_json_source(args.source))
    item = find_model(models, args.model)
    if not item:
        raise SystemExit(f"Model not found: {args.model}")
    if args.json:
        print(json.dumps(item, ensure_ascii=False, indent=2))
        return
    rows = [
        ["model_id", model_id(item)],
        ["name", model_label(item)],
        ["provider", developer(item)],
        ["context_length", context_display(item)],
        ["max_output", max_output_display(item)],
        ["pricing", pricing(item)],
        ["price_unit", price_unit()],
        ["types/endpoints", types(item)],
        ["features/modalities", features(item)],
    ]
    print_table(["field", "value"], rows)
    print("\nRaw model data is available with --json.")


def cmd_compare(args: argparse.Namespace) -> None:
    models = extract_models(load_json_source(args.source))
    selected = []
    missing = []
    for target in args.models:
        item = find_model(models, target)
        if item:
            selected.append(item)
        else:
            missing.append(target)
    if args.json:
        print(json.dumps({"models": selected, "missing": missing}, ensure_ascii=False, indent=2))
        return
    rows = []
    for item in selected:
        rows.append(
            [
                model_id(item),
                developer(item),
                context_display(item),
                max_output_display(item),
                pricing(item),
                features(item),
            ]
        )
    print_table(["model_id", "provider", "context", "max_output", "pricing", "features"], rows)
    if missing:
        print("\nmissing: " + ", ".join(missing))
    print(f"\nPricing units: {price_unit()}. Values are displayed exactly as returned by the models API.")


def cmd_latest_report(args: argparse.Namespace) -> None:
    payload = load_json_source(args.source)
    models = extract_models_in_source_order(payload)
    selected = models[: args.limit]
    if not selected:
        raise SystemExit("No models found in the selected source.")

    source = display_models_source()
    unit = price_unit()
    now = query_time_label()

    print(f"# AIHubMix Latest Models Report")
    print()
    print(f"- Data source: `{source}`")
    print(f"- Query time: `{now}`")
    print("- Latest definition: first records returned by `/api/v1/models` in source order; no model_id sorting is applied.")
    print(f"- Price unit: `{unit}`")
    print("- Price values: displayed exactly as returned in each model's `pricing` object.")
    print()
    print_user_overview(selected)
    print("| # | model_id | name | developer_id | pricing | context_length(tokens) | max_output(tokens) | types/endpoints | features | notes |")
    print("|---:|---|---|---:|---|---:|---:|---|---|---|")
    for index, item in enumerate(selected, start=1):
        type_endpoint = types(item)
        endpoints = compact(item.get("endpoints"))
        if endpoints != "-" and endpoints not in type_endpoint:
            type_endpoint = f"{type_endpoint}; endpoints={endpoints}" if type_endpoint != "-" else f"endpoints={endpoints}"
        print(
            "| "
            + " | ".join(
                [
                    str(index),
                    f"`{model_id(item)}`",
                    model_label(item).replace("|", "\\|"),
                    developer(item),
                    pricing(item).replace("|", "\\|"),
                    context_display(item),
                    max_output_display(item),
                    type_endpoint.replace("|", "\\|"),
                    features(item).replace("|", "\\|"),
                    availability_note(item).replace("|", "\\|"),
                ]
            )
            + " |"
        )
    print()
    print_model_switch_hint(selected)

    first_model = model_id(selected[0])
    protocol = suggested_protocol(selected[0])
    print()
    if protocol is None:
        print("## Example")
        print()
        print("The first selected model is not a plain text/chat model. Choose the endpoint by model type and verify it with `protocols` before generating a call example.")
        return

    print(f"## Suggested {protocol_name(protocol)} Call Example")
    print()
    print(f"- URL: `{base_url()}{endpoint_path(protocol, first_model)}`")
    print(f"- Auth: `{protocol_auth_label(protocol)}`")
    print("- Replace `model` with any compatible `model_id` from the table when needed.")
    print()
    os_name = detect_os(args.os)
    print(f"### Command Line ({'Windows PowerShell' if os_name == 'windows' else 'macOS/Linux shell'})")
    print()
    print(example_intro("command", os_name))
    print()
    print("```" + ("powershell" if os_name == "windows" else "bash"))
    print(render_cmd_example(protocol, first_model, os_name))
    print("```")
    print()
    print("### JavaScript")
    print()
    print(example_intro("js"))
    print()
    print_env_setup("js", os_name)
    print("```js")
    print(render_js_example(protocol, first_model))
    print("```")


def cmd_report(args: argparse.Namespace) -> None:
    payload = load_json_source(args.source)
    wants_latest = query_wants_latest(args.query)
    models = extract_models_in_source_order(payload) if wants_latest else extract_models(payload)
    selected, query_plan = rank_matching_models(
        models,
        args.query,
        limit=args.limit,
        preserve_source_order=wants_latest,
    )
    if not selected:
        raise SystemExit(f"No models matched query: {args.query}")

    source = display_models_source()
    now = query_time_label()
    matched_terms = "; ".join(query_plan["labels"]) if query_plan["labels"] else "raw query"

    print("# AIHubMix Model Interface Report")
    print()
    print(f"- Query: `{args.query}`")
    print(f"- Normalized query terms: `{matched_terms}`")
    if query_plan["wants_latest"]:
        print("- Latest intent: `detected`; matched rows keep `/api/v1/models` source order.")
    print(f"- Data source: `{source}`")
    print(f"- Query time: `{now}`")
    print(f"- Matched models shown: `{len(selected)}`")
    print(f"- Price unit: `{price_unit()}`")
    print("- Price values: displayed exactly as returned in each model's `pricing` object.")
    print()
    print_user_overview(selected, args.query)
    print("| model_id | name | developer_id | pricing | context | max_output | type | callable entrypoints | raw endpoints | features | modalities | notes |")
    print("|---|---|---:|---|---:|---:|---|---|---|---|---|---|")
    for item in selected:
        print(
            "| "
            + " | ".join(
                [
                    f"`{model_id(item)}`",
                    model_label(item).replace("|", "\\|"),
                    developer(item),
                    pricing(item).replace("|", "\\|"),
                    context_display(item),
                    max_output_display(item),
                    compact(item.get("types")).replace("|", "\\|"),
                    endpoint_display(item).replace("|", "\\|"),
                    endpoint_note(item).replace("|", "\\|"),
                    compact(item.get("features")).replace("|", "\\|"),
                    compact(item.get("input_modalities")).replace("|", "\\|"),
                    availability_note(item).replace("|", "\\|"),
                ]
            )
            + " |"
        )
    print()
    print_model_switch_hint(selected)

    first_model = model_id(selected[0])
    protocol = suggested_protocol(selected[0])
    print()
    if protocol is None:
        print("## Example")
        print()
        print("The matched model is not a plain text/chat model. Choose the endpoint by model type and verify it with `protocols` before generating a call example.")
        return

    print(f"## Suggested {protocol_name(protocol)} Endpoint")
    print()
    print("- Method: `POST`")
    print(f"- URL: `{base_url()}{endpoint_path(protocol, first_model)}`")
    print(f"- Auth: `{protocol_auth_label(protocol)}`")
    print()
    print("## Example")
    print()
    os_name = detect_os(args.os)
    print(f"### Command Line ({'Windows PowerShell' if os_name == 'windows' else 'macOS/Linux shell'})")
    print()
    print(example_intro("command", os_name))
    print()
    print("```" + ("powershell" if os_name == "windows" else "bash"))
    print(render_cmd_example(protocol, first_model, os_name))
    print("```")
    print()
    print("### JavaScript")
    print()
    print(example_intro("js"))
    print()
    print_env_setup("js", os_name)
    print("```js")
    print(render_js_example(protocol, first_model))
    print("```")


def load_openapi() -> dict[str, Any] | None:
    """Fetch the live OpenAPI spec from the remote endpoint (no local checkout)."""
    url = os.environ.get("AIHUBMIX_OPENAPI_URL") or OPENAPI_JSON_URL
    try:
        return json.loads(read_url_bytes(url).decode("utf-8", errors="replace"))
    except ValueError:
        return None


def _error_statuses_from_spec(spec: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Collect declared 4XX/5XX responses (code -> description/schema) from the spec."""
    statuses: dict[str, dict[str, str]] = {}
    for _method, _path, operation in iter_operations(spec):
        for code, response in (operation.get("responses") or {}).items():
            code = str(code)
            if code in statuses or not re.match(r"^[45]\d\d$|^[45]XX$", code, re.IGNORECASE):
                continue
            if not isinstance(response, dict):
                continue
            schema_ref = "#/components/schemas/GatewayError"
            for media in (response.get("content") or {}).values():
                ref = ((media or {}).get("schema") or {}).get("$ref")
                if ref:
                    schema_ref = ref
                    break
            statuses[code] = {
                "description": str(response.get("description", "")).strip(),
                "schema": schema_ref,
            }
    return statuses


def load_error_contract() -> dict[str, Any]:
    """Derive the GatewayError contract from the live OpenAPI spec (no local checkout)."""
    spec = load_openapi()
    if not spec:
        raise SystemExit(
            f"Could not load the OpenAPI spec from {OPENAPI_JSON_URL} to derive the error contract."
        )
    return {
        "source": display_error_contract_source(),
        "schema_name": "GatewayError",
        "envelope": {
            "top_level": "error",
            "required": ["error.message"],
            "fields": {
                "error.message": "Human-readable error message.",
                "error.type": "OpenAI-compatible category; upstream value may pass through and enum is not fixed.",
                "error.param": "Offending field name, when applicable.",
                "error.code": "Sub-error code; may be string or integer.",
            },
        },
        "request_id": "Use the X-Request-Id response header. It is not in the JSON body.",
        "legacy_upstream": "The legacy upstream field is no longer emitted.",
        "statuses": _error_statuses_from_spec(spec),
    }


def iter_operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    ops = []
    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if isinstance(operation, dict):
                ops.append((method.upper(), path, operation))
    return ops


def cmd_protocols(args: argparse.Namespace) -> None:
    spec = load_openapi()
    if not spec:
        raise SystemExit(f"Could not load the OpenAPI spec from {OPENAPI_JSON_URL}.")
    operations = iter_operations(spec)
    if args.json:
        print(json.dumps({"source": display_openapi_source(), "operations": operations}, ensure_ascii=False, indent=2))
        return
    rows = []
    for method, endpoint, operation in operations:
        security = operation.get("security") or spec.get("security") or []
        rows.append(
            [
                method,
                endpoint,
                operation.get("operationId", "-"),
                compact(security),
                "yes" if operation.get("requestBody") else "no",
            ]
        )
    print_table(["method", "path", "operation_id", "security", "request_body"], rows)
    print(f"\nsource: {display_openapi_source()}")


def cmd_error_contract(args: argparse.Namespace) -> None:
    contract = load_error_contract()
    if args.json:
        print(json.dumps(contract, ensure_ascii=False, indent=2))
        return

    print("# AIHubMix Gateway Error Contract")
    print()
    print(f"- Source: `{display_error_contract_source()}`")
    print(f"- Schema: `{contract['schema_name']}`")
    print("- Body shape: top-level `error` object.")
    print("- Required body field: `error.message`.")
    print(f"- Request ID: `{contract['request_id']}`")
    print(f"- Legacy upstream field: `{contract['legacy_upstream']}`")
    print()
    print("## GatewayError Fields")
    print()
    rows = [[field, description] for field, description in contract["envelope"]["fields"].items()]
    print_table(["field", "meaning"], rows)
    print()
    print("## Status Responses")
    print()
    status_order = ["400", "401", "403", "404", "429", "5XX"]
    rows = []
    statuses = contract["statuses"]
    for status in status_order:
        item = statuses.get(status, {})
        rows.append([status, item.get("description", "-"), item.get("schema", "#/components/schemas/GatewayError")])
    print_table(["status", "description", "schema"], rows)
    print()
    print("## Troubleshooting Rule")
    print()
    print("Use the live HTTP status, JSON error body, and `X-Request-Id` as the observed evidence.")
    print("Use this contract to verify the error envelope and status category; do not assume `error.type` is a fixed enum.")


def load_package_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else None


def find_installed_sdk_package(start: str | None = None) -> tuple[dict[str, Any] | None, Path | None]:
    explicit = os.environ.get("AIHUBMIX_SDK_PACKAGE_JSON")
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    cwd = Path(start).expanduser() if start else Path.cwd()
    for path in [cwd, *cwd.parents]:
        candidates.append(path / "node_modules" / "@aihubmix" / "ai-sdk-provider" / "package.json")
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        data = load_package_json(candidate)
        if data:
            return data, candidate
    return None, None


def fetch_npm_package_metadata() -> dict[str, Any] | None:
    request = urllib.request.Request(
        SDK_REGISTRY_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "aihubmixApi-skill/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} while checking npm registry: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not check npm registry: {exc.reason}") from exc
    return payload if isinstance(payload, dict) else None


def read_url_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "aihubmixApi-skill/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} while fetching {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not fetch {url}: {exc.reason}") from exc


def parse_sdk_package_texts(package_json: dict[str, Any], dts_text: str, js_text: str, source: str) -> dict[str, Any]:
    method_candidates = [
        "languageModel",
        "chat",
        "responses",
        "completion",
        "embedding",
        "embeddingModel",
        "image",
        "imageModel",
        "textEmbedding",
        "textEmbeddingModel",
        "transcription",
        "transcriptionModel",
        "speech",
        "speechModel",
    ]
    tool_candidates = ["codeInterpreter", "fileSearch", "imageGeneration", "webSearchPreview", "webSearch"]
    export_candidates = ["aihubmix", "createAihubmix"]
    provider_methods = [name for name in method_candidates if re.search(rf"\b{name}\b", dts_text)]
    tools = [name for name in tool_candidates if re.search(rf"\b{name}\b", dts_text)]
    exports = [name for name in export_candidates if re.search(rf"\b{name}\b", dts_text)]
    env_vars = sorted(set(re.findall(r'"(AIHUBMIX_[A-Z0-9_]+)"', js_text + dts_text)))
    base_urls = sorted(set(re.findall(r'"(https://aihubmix\.com[^"]*)"', js_text + dts_text)))
    header_candidates = ["Authorization", "APP-Code", "Content-Type", "x-api-key", "x-goog-api-key"]
    headers = [name for name in header_candidates if name in js_text]
    routing = []
    if 'startsWith("claude-")' in js_text:
        routing.append("Claude model IDs starting with claude- use Anthropic-compatible messages with x-api-key.")
    if 'startsWith("gemini")' in js_text or 'startsWith("imagen")' in js_text:
        routing.append("Gemini or Imagen model IDs use Gemini native base URL unless suffixed with -nothink or -search.")
    if "OpenAICompatibleChatLanguageModel" in js_text:
        routing.append("Other chat models use OpenAI-compatible chat through https://aihubmix.com/v1.")

    return {
        "source": source,
        "package": str(package_json.get("name") or SDK_PACKAGE_NAME),
        "version": str(package_json.get("version") or "-"),
        "exports": exports,
        "provider_methods": provider_methods,
        "tools": tools,
        "environment_variable": env_vars[0] if env_vars else "-",
        "base_urls": base_urls,
        "headers": headers,
        "routing": routing,
    }


def load_sdk_info_from_directory(package_dir: Path, source_label: str) -> dict[str, Any]:
    package_json = load_package_json(package_dir / "package.json") or {}
    dts_text = (package_dir / "dist" / "index.d.ts").read_text(encoding="utf-8")
    js_text = (package_dir / "dist" / "index.js").read_text(encoding="utf-8")
    return parse_sdk_package_texts(package_json, dts_text, js_text, source_label)


def load_sdk_info_from_tarball(tarball: bytes, source_label: str) -> dict[str, Any]:
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        files: dict[str, bytes] = {}
        for name in ("package/package.json", "package/dist/index.d.ts", "package/dist/index.js"):
            member = archive.getmember(name)
            extracted = archive.extractfile(member)
            if not extracted:
                raise SystemExit(f"Could not read {name} from SDK tarball.")
            files[name] = extracted.read()
    package_json = json.loads(files["package/package.json"].decode("utf-8"))
    dts_text = files["package/dist/index.d.ts"].decode("utf-8")
    js_text = files["package/dist/index.js"].decode("utf-8")
    return parse_sdk_package_texts(package_json, dts_text, js_text, source_label)


def load_sdk_info(args: argparse.Namespace) -> dict[str, Any]:
    if args.package_dir:
        return load_sdk_info_from_directory(Path(args.package_dir).expanduser(), str(Path(args.package_dir).expanduser()))

    installed, package_json_path = find_installed_sdk_package(args.project)
    if package_json_path and args.source in {"auto", "installed"}:
        return load_sdk_info_from_directory(package_json_path.parent, str(package_json_path.parent))
    if args.source == "installed":
        raise SystemExit("SDK package is not installed in the selected project path.")

    metadata = fetch_npm_package_metadata()
    target_version = args.version or SDK_RECOMMENDED_VERSION
    versions = metadata.get("versions") or {}
    package_meta = versions.get(target_version)
    if not isinstance(package_meta, dict):
        raise SystemExit(f"Could not find {SDK_PACKAGE_NAME}@{target_version} in npm registry metadata.")
    tarball_url = ((package_meta.get("dist") or {}).get("tarball"))
    if not tarball_url:
        raise SystemExit(f"No tarball URL found for {SDK_PACKAGE_NAME}@{target_version}.")
    return load_sdk_info_from_tarball(read_url_bytes(str(tarball_url)), f"npm tarball {SDK_PACKAGE_NAME}@{target_version}")


def cmd_sdk_info(args: argparse.Namespace) -> None:
    info = load_sdk_info(args)
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    print("# AIHubMix SDK Provider Info")
    print()
    print(f"- Package: `{info['package']}`")
    print(f"- Version: `{info['version']}`")
    print(f"- Source: `{info['source']}`")
    print("- Data role: SDK/provider usage source; not model price, context, or availability source.")
    print()
    print("## Provider Surface")
    print()
    rows = []
    for name in info["provider_methods"]:
        if name in {"chat", "languageModel"}:
            purpose = "text/chat generation"
        elif name == "responses":
            purpose = "OpenAI Responses API style model"
        elif "embedding" in name.lower():
            purpose = "text embeddings"
        elif name.startswith("image"):
            purpose = "image generation"
        elif "transcription" in name.lower():
            purpose = "audio transcription"
        elif "speech" in name.lower():
            purpose = "speech synthesis"
        elif name == "completion":
            purpose = "legacy text completion"
        else:
            purpose = "provider method"
        rows.append([name, purpose])
    print_table(["method", "purpose"], rows)
    print()
    print("## Tools")
    print()
    print(", ".join(info["tools"]) if info["tools"] else "-")
    print()
    print("## Auth And Routing")
    print()
    print_table(
        ["field", "value"],
        [
            ["api_key_env", info["environment_variable"]],
            ["base_urls", compact(info["base_urls"])],
            ["headers", compact(info["headers"])],
            ["exports", compact(info["exports"])],
        ],
    )
    if info["routing"]:
        print()
        print("## Routing Notes")
        for index, item in enumerate(info["routing"], start=1):
            print(f"{index}. {item}")
    print()
    print("## Boundary")
    print("Use `/api/v1/models` for live model price/context/availability. Use this SDK info for JavaScript provider usage.")


def version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in version.split("."):
        digits = ""
        for char in part:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits or 0))
    return tuple(parts)


def cmd_sdk_check(args: argparse.Namespace) -> None:
    installed, installed_path = find_installed_sdk_package(args.project)
    installed_version = str(installed.get("version")) if installed else "-"
    latest_version = "-"
    registry_source = SDK_REGISTRY_URL
    metadata = None
    if not args.offline:
        metadata = fetch_npm_package_metadata()
        latest_version = str((metadata.get("dist-tags") or {}).get("latest") or "-")
    target_version = args.version or SDK_RECOMMENDED_VERSION

    print("# AIHubMix SDK Check")
    print()
    print(f"- Package: `{SDK_PACKAGE_NAME}`")
    print(f"- Recommended version for this skill: `{SDK_RECOMMENDED_VERSION}`")
    print(f"- Target version: `{target_version}`")
    print(f"- Installed version: `{installed_version}`")
    print(f"- Installed package.json: `{installed_path or '-'}`")
    print(f"- Registry latest: `{latest_version}`")
    print(f"- Registry source: `{registry_source if not args.offline else 'not checked (--offline)'}`")
    print("- Auto update: `not performed`")

    status = []
    if installed_version == "-":
        status.append("SDK is not installed in the selected project path.")
    elif installed_version == target_version:
        status.append("Installed SDK matches the target version.")
    else:
        status.append("Installed SDK differs from the target version.")

    if latest_version != "-":
        if version_tuple(latest_version) > version_tuple(target_version):
            status.append("A newer npm version is available; review changelog before updating.")
        elif latest_version == target_version:
            status.append("Target version is the npm latest version.")
        else:
            status.append("Target version is newer than registry latest; verify the package tag.")
    else:
        status.append("Latest npm version was not checked.")

    print()
    print("## Status")
    for item in status:
        print(f"- {item}")

    print()
    print("## Manual Commands")
    print()
    print("```bash")
    print(f"npm view {SDK_PACKAGE_NAME} version")
    print(f"npm install {SDK_PACKAGE_NAME}@{target_version} ai")
    print("```")
    print()
    print("Only run install/update commands after the user confirms the target project and version.")


def base_url() -> str:
    return os.environ.get("AIHUBMIX_BASE_URL", DEFAULT_SERVER_URL).rstrip("/")


def normalize_protocol(protocol: str) -> str:
    normalized = PROTOCOL_ALIASES.get(protocol, protocol)
    if normalized not in PROTOCOL_SPECS:
        raise ValueError(normalized)
    return normalized


def endpoint_path(protocol: str, model: str) -> str:
    protocol = normalize_protocol(protocol)
    path = PROTOCOL_SPECS[protocol]["path"]
    return path.replace("{model}", model).replace("{video_id}", "video_123")


def example_payload(protocol: str, model: str) -> dict[str, Any]:
    protocol = normalize_protocol(protocol)
    if protocol == "chat":
        return {
            "model": model,
            "messages": [{"role": "user", "content": "Say hello in one short sentence."}],
        }
    if protocol == "responses":
        return {"model": model, "input": "Say hello in one short sentence."}
    if protocol == "messages":
        return {
            "model": model,
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "Say hello in one short sentence."}],
        }
    if protocol == "gemini":
        return {"contents": [{"role": "user", "parts": [{"text": "Say hello in one short sentence."}]}]}
    if protocol == "completions":
        return {"model": model, "prompt": "Say hello in one short sentence.", "max_tokens": 64}
    if protocol == "embeddings":
        return {"model": model, "input": "Text to embed with AIHubMix."}
    if protocol == "images":
        return {"model": model, "prompt": "A clean product mockup on a white background.", "size": "1024x1024"}
    if protocol == "videos":
        return {"model": model, "prompt": "A short cinematic shot of a city at sunrise."}
    if protocol == "video-remix":
        return {"model": model, "prompt": "Make the video brighter and more cinematic."}
    if protocol == "audio-speech":
        return {"model": model, "input": "Hello from AIHubMix.", "voice": "alloy", "response_format": "mp3"}
    if protocol in {"audio-transcriptions", "audio-translations"}:
        return {"model": model, "file": "@/path/to/audio.mp3"}
    if protocol == "moderations":
        return {"model": model, "input": "I want to check whether this text is safe."}
    if protocol in {"video-retrieve", "video-delete", "video-content"}:
        return {}
    raise ValueError(protocol)


def auth_header(protocol: str) -> tuple[str, str]:
    protocol = normalize_protocol(protocol)
    family = PROTOCOL_SPECS[protocol]["family"]
    if family == "anthropic":
        return "x-api-key", "$AIHUBMIX_API_KEY"
    if family == "gemini":
        return "x-goog-api-key", "$AIHUBMIX_API_KEY"
    return "Authorization", "Bearer $AIHUBMIX_API_KEY"


def detect_os(requested: str) -> str:
    if requested != "auto":
        return requested
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    if system == "darwin":
        return "mac"
    return "linux"


def powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def powershell_response_printer() -> str:
    return (
        "if ($response.choices -and $response.choices.Count -gt 0) {\n"
        "  [Console]::WriteLine($response.choices[0].message.content)\n"
        "} elseif ($response.output_text) {\n"
        "  [Console]::WriteLine($response.output_text)\n"
        "} elseif ($response.content -and $response.content.Count -gt 0) {\n"
        "  [Console]::WriteLine($response.content[0].text)\n"
        "} elseif ($response.candidates -and $response.candidates.Count -gt 0) {\n"
        "  [Console]::WriteLine($response.candidates[0].content.parts[0].text)\n"
        "} else {\n"
        "  $response | ConvertTo-Json -Depth 20\n"
        "}\n"
    )


def powershell_response_printer_for(protocol: str) -> str:
    protocol = normalize_protocol(protocol)
    if protocol == "embeddings":
        return (
            "if ($response.data -and $response.data.Count -gt 0) {\n"
            "  [Console]::WriteLine(\"embedding dimensions: \" + $response.data[0].embedding.Count)\n"
            "} else {\n"
            "  $response | ConvertTo-Json -Depth 20\n"
            "}\n"
        )
    if protocol == "images":
        return (
            "if ($response.data -and $response.data.Count -gt 0) {\n"
            "  $item = $response.data[0]\n"
            "  if ($item.url) { [Console]::WriteLine($item.url) } elseif ($item.b64_json) { [Console]::WriteLine($item.b64_json) } else { $item | ConvertTo-Json -Depth 20 }\n"
            "} else {\n"
            "  $response | ConvertTo-Json -Depth 20\n"
            "}\n"
        )
    if protocol in {"videos", "video-remix", "video-retrieve"}:
        return (
            "if ($response.id) {\n"
            "  [Console]::WriteLine(\"video id: \" + $response.id)\n"
            "} else {\n"
            "  $response | ConvertTo-Json -Depth 20\n"
            "}\n"
        )
    if protocol in {"audio-transcriptions", "audio-translations"}:
        return (
            "if ($response.text) {\n"
            "  [Console]::WriteLine($response.text)\n"
            "} else {\n"
            "  $response | ConvertTo-Json -Depth 20\n"
            "}\n"
        )
    if protocol == "moderations":
        return (
            "if ($response.results -and $response.results.Count -gt 0) {\n"
            "  $response.results[0] | ConvertTo-Json -Depth 20\n"
            "} else {\n"
            "  $response | ConvertTo-Json -Depth 20\n"
            "}\n"
        )
    return powershell_response_printer()


def shell_response_parser() -> str:
    return (
        "import json,sys; d=json.load(sys.stdin); "
        "text=(d.get('output_text') or ((d.get('choices') or [{}])[0].get('message') or {}).get('content') "
        "or ((d.get('content') or [{}])[0]).get('text') "
        "or ((((d.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [{}])[0]).get('text')); "
        "print(text if text is not None else json.dumps(d, ensure_ascii=False))"
    )


def shell_response_parser_for(protocol: str) -> str:
    protocol = normalize_protocol(protocol)
    if protocol == "embeddings":
        return (
            "import json,sys; d=json.load(sys.stdin); data=d.get('data') or []; "
            "print('embedding dimensions: ' + str(len((data[0] if data else {}).get('embedding') or [])))"
        )
    if protocol == "images":
        return (
            "import json,sys; d=json.load(sys.stdin); item=(d.get('data') or [{}])[0]; "
            "print(item.get('url') or item.get('b64_json') or json.dumps(d, ensure_ascii=False))"
        )
    if protocol in {"videos", "video-remix", "video-retrieve"}:
        return (
            "import json,sys; d=json.load(sys.stdin); "
            "print(('video id: ' + str(d.get('id'))) if d.get('id') else json.dumps(d, ensure_ascii=False))"
        )
    if protocol in {"audio-transcriptions", "audio-translations"}:
        return "import json,sys; d=json.load(sys.stdin); print(d.get('text') or json.dumps(d, ensure_ascii=False))"
    if protocol == "moderations":
        return (
            "import json,sys; d=json.load(sys.stdin); "
            "print(json.dumps((d.get('results') or [d])[0], ensure_ascii=False))"
        )
    return shell_response_parser()


def render_cmd_example(protocol: str, model: str, os_name: str) -> str:
    protocol = normalize_protocol(protocol)
    url = base_url() + endpoint_path(protocol, model)
    payload = example_payload(protocol, model)
    spec = PROTOCOL_SPECS[protocol]
    method = spec["method"]
    is_get_or_delete = method in {"GET", "DELETE"}
    is_multipart = bool(spec.get("multipart"))
    is_binary = bool(spec.get("binary_response") or protocol == "video-content")
    needs_video_id = bool(spec.get("needs_video_id"))
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    header_name, _ = auth_header(protocol)

    if os_name == "windows":
        if spec["family"] == "anthropic":
            auth_line = '"x-api-key" = $AIHUBMIX_API_KEY'
        elif spec["family"] == "gemini":
            auth_line = '"x-goog-api-key" = $AIHUBMIX_API_KEY'
        else:
            auth_line = '"Authorization" = "Bearer $AIHUBMIX_API_KEY"'
        if is_get_or_delete:
            if is_binary:
                return (
                    "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
                    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12\n"
                    "$AIHUBMIX_API_KEY = Read-Host \"Paste AIHubMix API Key\"\n"
                    "$videoId = Read-Host \"Paste video id\"\n"
                    f"$url = {powershell_literal(url)}.Replace('video_123', $videoId)\n\n"
                    "Invoke-WebRequest `\n"
                    "  -Uri $url `\n"
                    "  -Method Get `\n"
                    f"  -Headers @{{ {auth_line} }} `\n"
                    "  -OutFile 'aihubmix-video.mp4'\n\n"
                    "[Console]::WriteLine('Saved to aihubmix-video.mp4')"
                )
            return (
                "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12\n"
                "$AIHUBMIX_API_KEY = Read-Host \"Paste AIHubMix API Key\"\n"
                "$videoId = Read-Host \"Paste video id\"\n"
                f"$url = {powershell_literal(url)}.Replace('video_123', $videoId)\n\n"
                "$response = Invoke-RestMethod `\n"
                "  -Uri $url `\n"
                f"  -Method {method.title()} `\n"
                f"  -Headers @{{ {auth_line}; \"Accept\" = \"application/json\" }}\n\n"
                f"{powershell_response_printer_for(protocol)}"
            )
        if is_multipart:
            return (
                "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12\n"
                "$AIHUBMIX_API_KEY = Read-Host \"Paste AIHubMix API Key\"\n"
                "$audioPath = Read-Host \"Paste local audio file path\"\n\n"
                "$form = @{\n"
                f"  model = {powershell_literal(model)}\n"
                "  file = Get-Item -LiteralPath $audioPath\n"
                "}\n\n"
                "$response = Invoke-RestMethod `\n"
                f"  -Uri {powershell_literal(url)} `\n"
                "  -Method Post `\n"
                f"  -Headers @{{ {auth_line}; \"Accept\" = \"application/json\" }} `\n"
                "  -Form $form\n\n"
                f"{powershell_response_printer_for(protocol)}"
            )
        if needs_video_id:
            return (
                "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::InputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12\n"
                "$AIHUBMIX_API_KEY = Read-Host \"Paste AIHubMix API Key\"\n"
                "$videoId = Read-Host \"Paste video id\"\n"
                f"$url = {powershell_literal(url)}.Replace('video_123', $videoId)\n\n"
                "$body = @'\n"
                f"{body}\n"
                "'@\n\n"
                "$response = Invoke-RestMethod `\n"
                "  -Uri $url `\n"
                f"  -Method {method.title()} `\n"
                f"  -Headers @{{ {auth_line}; \"Accept\" = \"application/json\" }} `\n"
                "  -ContentType \"application/json\" `\n"
                "  -Body $body\n\n"
                f"{powershell_response_printer_for(protocol)}\n"
                "# To inspect the full response, uncomment the next line:\n"
                "# $response | ConvertTo-Json -Depth 20"
            )
        if is_binary:
            return (
                "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12\n"
                "$AIHUBMIX_API_KEY = Read-Host \"Paste AIHubMix API Key\"\n\n"
                "$body = @'\n"
                f"{body}\n"
                "'@\n\n"
                "Invoke-WebRequest `\n"
                f"  -Uri {powershell_literal(url)} `\n"
                "  -Method Post `\n"
                f"  -Headers @{{ {auth_line} }} `\n"
                "  -ContentType \"application/json\" `\n"
                "  -Body $body `\n"
                "  -OutFile 'aihubmix-output.mp3'\n\n"
                "[Console]::WriteLine('Saved to aihubmix-output.mp3')"
            )
        return (
            "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
            "[Console]::InputEncoding = [System.Text.Encoding]::UTF8\n"
            "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12\n"
            "$AIHUBMIX_API_KEY = Read-Host \"Paste AIHubMix API Key\"\n\n"
            "$body = @'\n"
            f"{body}\n"
            "'@\n\n"
            "$response = Invoke-RestMethod `\n"
            f"  -Uri {powershell_literal(url)} `\n"
            "  -Method Post `\n"
            f"  -Headers @{{ {auth_line}; \"Accept\" = \"application/json\" }} `\n"
            "  -ContentType \"application/json\" `\n"
            "  -Body $body\n\n"
            f"{powershell_response_printer_for(protocol)}\n"
            "# To inspect the full response, uncomment the next line:\n"
            "# $response | ConvertTo-Json -Depth 20"
        )

    if spec["family"] == "anthropic":
        auth_arg = '-H "x-api-key: $AIHUBMIX_API_KEY"'
    elif spec["family"] == "gemini":
        auth_arg = '-H "x-goog-api-key: $AIHUBMIX_API_KEY"'
    else:
        auth_arg = '-H "Authorization: Bearer $AIHUBMIX_API_KEY"'
    if is_get_or_delete:
        if is_binary:
            return textwrap.dedent(
                f"""\
                read -rsp "Paste AIHubMix API Key: " AIHUBMIX_API_KEY; echo
                read -rp "Paste video id: " video_id

                curl -L -s {json.dumps(url)} \\
                  {auth_arg} \\
                  -o aihubmix-video.mp4

                echo "Saved to aihubmix-video.mp4"
                """
            ).strip().replace("video_123", "${video_id}")
        return textwrap.dedent(
            f"""\
            read -rsp "Paste AIHubMix API Key: " AIHUBMIX_API_KEY; echo
            read -rp "Paste video id: " video_id

            curl -s -X {method} {json.dumps(url)} \\
              {auth_arg} \\
              -H "Accept: application/json" \\
              | python3 -c {json.dumps(shell_response_parser_for(protocol))}
            """
        ).strip().replace("video_123", "${video_id}")
    if is_multipart:
        return textwrap.dedent(
            f"""\
            read -rsp "Paste AIHubMix API Key: " AIHUBMIX_API_KEY; echo
            read -rp "Paste local audio file path: " audio_path

            curl -s {json.dumps(url)} \\
              {auth_arg} \\
              -H "Accept: application/json" \\
              -F model={json.dumps(model)} \\
              -F file=@"$audio_path" \\
              | python3 -c {json.dumps(shell_response_parser_for(protocol))}
            """
        ).strip()
    if needs_video_id:
        compact_payload_video = json.dumps(payload, ensure_ascii=False)
        return textwrap.dedent(
            f"""\
            read -rsp "Paste AIHubMix API Key: " AIHUBMIX_API_KEY; echo
            read -rp "Paste video id: " video_id

            curl -s -X {method} {json.dumps(url)} \\
              {auth_arg} \\
              -H "Content-Type: application/json" \\
              -d {json.dumps(compact_payload_video)} \\
              | python3 -c {json.dumps(shell_response_parser_for(protocol))}
            """
        ).strip().replace("video_123", "${video_id}")
    if is_binary:
        compact_payload_binary = json.dumps(payload, ensure_ascii=False)
        return textwrap.dedent(
            f"""\
            read -rsp "Paste AIHubMix API Key: " AIHUBMIX_API_KEY; echo

            curl -L -s {json.dumps(url)} \\
              {auth_arg} \\
              -H "Content-Type: application/json" \\
              -d {json.dumps(compact_payload_binary)} \\
              -o aihubmix-output.mp3

            echo "Saved to aihubmix-output.mp3"
            """
        ).strip()
    compact_payload = json.dumps(payload, ensure_ascii=False)
    return textwrap.dedent(
        f"""\
        read -rsp "Paste AIHubMix API Key: " AIHUBMIX_API_KEY; echo

        curl -s {json.dumps(url)} \\
          {auth_arg} \\
          -H "Content-Type: application/json" \\
          -d {json.dumps(compact_payload)} \\
          | python3 -c {json.dumps(shell_response_parser_for(protocol))}
        """
    ).strip()


def render_js_example(protocol: str, model: str) -> str:
    protocol = normalize_protocol(protocol)
    if protocol == "chat":
        return textwrap.dedent(
            f"""\
            import {{ aihubmix }} from "@aihubmix/ai-sdk-provider";
            import {{ generateText }} from "ai";

            const {{ text }} = await generateText({{
              model: aihubmix({json.dumps(model)}),
              prompt: "Say hello in one short sentence.",
            }});

            console.log(text);
            """
        ).strip()

    payload = example_payload(protocol, model)
    path = endpoint_path(protocol, model)
    spec = PROTOCOL_SPECS[protocol]
    header_name, header_value = auth_header(protocol)
    header_value_js = (
        "process.env.AIHUBMIX_API_KEY"
        if spec["family"] in {"anthropic", "gemini"}
        else '`Bearer ${process.env.AIHUBMIX_API_KEY}`'
    )
    payload_js = json.dumps(payload, ensure_ascii=False, indent=2)
    payload_body_lines = ["  body: JSON.stringify(" + payload_js.splitlines()[0]]
    payload_body_lines.extend("  " + line for line in payload_js.splitlines()[1:])
    payload_body_lines[-1] = payload_body_lines[-1] + "),"
    if spec.get("multipart"):
        return textwrap.dedent(
            f"""\
            import {{ createReadStream }} from "node:fs";

            const form = new FormData();
            form.set("model", {json.dumps(model)});
            form.set("file", createReadStream(process.env.AUDIO_FILE ?? "./audio.mp3"));

            const response = await fetch("{base_url()}{path}", {{
              method: "POST",
              headers: {{
                {json.dumps(header_name)}: {header_value_js},
              }},
              body: form,
            }});

            if (!response.ok) {{
              throw new Error(`${{response.status}} ${{await response.text()}}`);
            }}

            const data = await response.json();
            console.log(data.text ?? JSON.stringify(data, null, 2));
            """
        ).strip()
    if spec.get("binary_response"):
        return "\n".join(
            [
                'import { writeFile } from "node:fs/promises";',
                "",
                f'const response = await fetch("{base_url()}{path}", {{',
                '  method: "POST",',
                "  headers: {",
                f"    {json.dumps(header_name)}: {header_value_js},",
                '    "Content-Type": "application/json",',
                "  },",
                *payload_body_lines,
                "});",
                "",
                "if (!response.ok) {",
                "  throw new Error(`${response.status} ${await response.text()}`);",
                "}",
                "",
                'await writeFile("aihubmix-output.mp3", Buffer.from(await response.arrayBuffer()));',
                'console.log("Saved to aihubmix-output.mp3");',
            ]
        )
    if protocol == "video-content":
        return textwrap.dedent(
            f"""\
            import {{ writeFile }} from "node:fs/promises";

            const videoId = process.env.AIHUBMIX_VIDEO_ID ?? "video_123";
            const response = await fetch("{base_url()}{path}".replace("video_123", videoId), {{
              method: "GET",
              headers: {{
                {json.dumps(header_name)}: {header_value_js},
              }},
            }});

            if (!response.ok) {{
              throw new Error(`${{response.status}} ${{await response.text()}}`);
            }}

            await writeFile("aihubmix-video.mp4", Buffer.from(await response.arrayBuffer()));
            console.log("Saved to aihubmix-video.mp4");
            """
        ).strip()
    if spec["method"] in {"GET", "DELETE"}:
        return textwrap.dedent(
            f"""\
            const videoId = process.env.AIHUBMIX_VIDEO_ID ?? "video_123";
            const response = await fetch("{base_url()}{path}".replace("video_123", videoId), {{
              method: {json.dumps(spec["method"])},
              headers: {{
                {json.dumps(header_name)}: {header_value_js},
                "Accept": "application/json",
              }},
            }});

            if (!response.ok) {{
              throw new Error(`${{response.status}} ${{await response.text()}}`);
            }}

            const data = await response.json();
            console.log(data.id ? `video id: ${{data.id}}` : JSON.stringify(data, null, 2));
            """
        ).strip()
    if spec.get("needs_video_id"):
        path_expr = f'"{base_url()}{path}".replace("video_123", videoId)'
        return "\n".join(
            [
                'const videoId = process.env.AIHUBMIX_VIDEO_ID ?? "video_123";',
                f"const response = await fetch({path_expr}, {{",
                f'  method: {json.dumps(spec["method"])},',
                "  headers: {",
                f"    {json.dumps(header_name)}: {header_value_js},",
                '    "Content-Type": "application/json",',
                "  },",
                *payload_body_lines,
                "});",
                "",
                "if (!response.ok) {",
                "  throw new Error(`${response.status} ${await response.text()}`);",
                "}",
                "",
                "const data = await response.json();",
                "console.log(data.id ? `video id: ${data.id}` : JSON.stringify(data, null, 2));",
            ]
        )
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    payload_lines = ["  body: JSON.stringify(" + payload_json.splitlines()[0]]
    payload_lines.extend("  " + line for line in payload_json.splitlines()[1:])
    payload_lines[-1] = payload_lines[-1] + "),"
    return "\n".join(
        [
            f'const response = await fetch("{base_url()}{path}", {{',
            f'  method: {json.dumps(spec["method"])},',
            "  headers: {",
            f"    {json.dumps(header_name)}: {header_value_js},",
            '    "Content-Type": "application/json",',
            "  },",
            *payload_lines,
            "});",
            "",
            "if (!response.ok) {",
            "  throw new Error(`${response.status} ${await response.text()}`);",
            "}",
            "",
            "const data = await response.json();",
            "const text =",
            "  data.output_text ??",
            "  data.choices?.[0]?.message?.content ??",
            "  data.content?.[0]?.text ??",
            "  data.candidates?.[0]?.content?.parts?.[0]?.text ??",
            "  data.data?.[0]?.url ??",
            "  data.data?.[0]?.b64_json ??",
            "  data.text ??",
            "  (data.id ? `video id: ${data.id}` : undefined);",
            "",
            "console.log(text ?? JSON.stringify(data, null, 2));",
        ]
    )


def cmd_example(args: argparse.Namespace) -> None:
    protocol = args.protocol
    model = args.model
    os_name = detect_os(args.os)
    if args.lang == "both":
        print(f"## Command Line ({'Windows PowerShell' if os_name == 'windows' else 'macOS/Linux shell'})")
        print()
        print(example_intro("command", os_name))
        print()
        print("```" + ("powershell" if os_name == "windows" else "bash"))
        print(render_cmd_example(protocol, model, os_name))
        print("```")
        print()
        print("## JavaScript")
        print()
        print(example_intro("js"))
        print()
        print_env_setup("js", os_name)
        print("```js")
        print(render_js_example(protocol, model))
        print("```")
        return

    url = base_url() + endpoint_path(protocol, model)
    payload = example_payload(protocol, model)
    header_name, header_value = auth_header(protocol)
    body = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.lang == "json":
        print(body)
        return

    if args.lang == "curl":
        print(render_cmd_example(protocol, model, os_name))
        return

    if args.lang == "python":
        if normalize_protocol(protocol) == "chat":
            print(
                textwrap.dedent(
                    f"""\
                    import os
                    from openai import OpenAI

                    client = OpenAI(
                        api_key=os.environ["AIHUBMIX_API_KEY"],
                        base_url="{base_url()}/v1",
                    )

                    response = client.chat.completions.create(
                        model={model!r},
                        messages=[{{"role": "user", "content": "Say hello in one short sentence."}}],
                    )
                    print(response.choices[0].message.content)
                    """
                ).strip()
            )
        else:
            print("# Use the command-line or JavaScript example for this endpoint shape.")
        return

    if args.lang == "js":
        print(render_js_example(protocol, model))
        return

    raise ValueError(args.lang)


def parse_error_body(body_text: str | None, body_file: str | None) -> dict[str, Any] | None:
    if body_file:
        body_text = Path(body_file).read_text(encoding="utf-8")
    if not body_text:
        return None
    try:
        data = json.loads(body_text)
        return data if isinstance(data, dict) else {"raw": data}
    except json.JSONDecodeError:
        return {"raw": body_text}


def cmd_troubleshoot(args: argparse.Namespace) -> None:
    body = parse_error_body(args.body, args.body_file)
    error = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), dict) else {}
    message = error.get("message") or (body or {}).get("message") if isinstance(body, dict) else None
    kind = error.get("type")
    param = error.get("param")
    code = error.get("code")

    print("Observed")
    print_table(
        ["field", "value"],
        [
            ["status", str(args.status or "-")],
            ["endpoint", args.endpoint or "-"],
            ["model", args.model or "-"],
            ["error.type", str(kind or "-")],
            ["error.param", str(param or "-")],
            ["error.code", str(code or "-")],
            ["error.message", str(message or "-")],
            ["request_id", args.request_id or "check X-Request-Id response header"],
        ],
    )

    if args.contract:
        contract = load_error_contract()
        status_key = "5XX" if args.status and args.status >= 500 else str(args.status or "")
        status_contract = contract["statuses"].get(status_key, {})
        is_gateway_shape = isinstance(error, dict) and bool(message)
        print("\nContract Match")
        print_table(
            ["field", "value"],
            [
                ["contract_source", display_error_contract_source()],
                ["schema", contract["schema_name"]],
                ["status_contract", status_contract.get("description", "not declared")],
                ["body_shape", "GatewayError-like" if is_gateway_shape else "not enough evidence"],
                ["request_id_rule", contract["request_id"]],
                ["error_type_rule", contract["envelope"]["fields"]["error.type"]],
            ],
        )

    print("\nSuggested checks")
    suggestions = []
    status = args.status
    if status in (401, 403):
        suggestions.extend(
            [
                "Confirm AIHUBMIX_API_KEY is present and sent with the right header for the endpoint.",
                "Use Authorization: Bearer for OpenAI-shaped endpoints, x-api-key for /v1/messages, and x-goog-api-key or ?key= for Gemini-shaped endpoints.",
            ]
        )
    elif status == 404:
        suggestions.extend(
            [
                "Confirm the endpoint path matches the protocol contract.",
                "Confirm the model exists in /api/v1/models and the model ID is copied exactly.",
            ]
        )
    elif status == 400:
        suggestions.extend(
            [
                "Validate the request body against aihubmix-openapi openapi.json or contract.json.",
                "Check whether the model supports the requested endpoint, modality, and feature fields.",
            ]
        )
    elif status == 429:
        suggestions.append("Check rate limits, quota, and retry policy before re-sending the same request.")
    elif status and status >= 500:
        suggestions.extend(
            [
                "Treat this as gateway or upstream failure; preserve status, error body, and X-Request-Id.",
                "Retry only when the operation is idempotent or the client can tolerate duplicate work.",
            ]
        )
    else:
        suggestions.append("Start with status, error body, endpoint, model ID, and X-Request-Id.")

    if args.model:
        suggestions.append("Run `models get <model_id>` to inspect context_length, max_output, endpoints, and features.")
    if args.endpoint:
        suggestions.append("Run `protocols` to inspect the endpoint security scheme and requestBody contract.")
    for index, item in enumerate(suggestions, start=1):
        print(f"{index}. {item}")


# --- Preflight (doctor) + image-input candidates --------------------------


def _openai_base(explicit: str | None = None) -> str:
    """OpenAI-compatible base URL, tolerant of a trailing /v1 already present."""
    raw = (explicit or os.environ.get("AIHUBMIX_BASE_URL") or DEFAULT_SERVER_URL).rstrip("/")
    return raw if raw.endswith("/v1") else raw + "/v1"


def _http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 30,
) -> tuple[int | None, str]:
    """Minimal JSON HTTP call. Returns (status, text); status is None on network error."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            return status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return None, f"URLError: {exc.reason}"
    except (TimeoutError, OSError) as exc:
        return None, f"network error: {exc}"


def _mask_secret(secret: str) -> str:
    secret = (secret or "").strip()
    if not secret:
        return "(none)"
    if len(secret) <= 12:
        return secret[:2] + "…" + secret[-2:]
    return secret[:5] + "…" + secret[-4:]


def _redact(text: str, *secrets: str) -> str:
    """Scrub keys from upstream text (AIHubMix echoes the key in invalid-key errors)."""
    out = text or ""
    for secret in secrets:
        secret = (secret or "").strip()
        if len(secret) >= 6:
            out = out.replace(secret, "[REDACTED]")
            if secret.lower().startswith("sk-"):
                out = out.replace(secret[3:], "[REDACTED]")
    return re.sub(r"sk-[A-Za-z0-9]{6,}", "[REDACTED]", out)


def _extract_chat_reply(body: str) -> str | None:
    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
    return str(content).strip()


def _looks_like_auth_error(body: str) -> bool:
    low = (body or "").lower()
    return any(
        token in low
        for token in (
            "invalid key", "invalid api key", "incorrect api key", "unauthorized",
            "authentication", "no permission", "无效", "鉴权", "未授权", "令牌",
        )
    )


def _looks_like_balance_error(body: str) -> bool:
    low = (body or "").lower()
    return any(
        token in low
        for token in (
            "insufficient balance", "insufficient_quota", "insufficient funds", "no balance",
            "balance is not enough", "arrearage", "余额不足", "余额已用", "欠费", "额度不足",
        )
    )


def _solid_png_data_url(rgb: tuple[int, int, int] = (20, 90, 210), size: int = 64) -> str:
    """Build a tiny solid-color PNG data URL (stdlib only) for probing image input."""
    import base64
    import struct
    import zlib

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b"".join(b"\x00" + bytes(rgb) * size for _ in range(size))
    png = signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def cmd_doctor(args: argparse.Namespace) -> int:
    key = (args.key or os.environ.get("AIHUBMIX_API_KEY") or "").strip()
    base = _openai_base(args.base_url)
    timeout = args.timeout

    print(_t("AIHubMix preflight (doctor)", "AIHubMix 预检 (doctor)"))
    print(f"base_url: {base}")
    print(f"key: {_mask_secret(key)}\n")

    if not key:
        print(_t("[✗] KEY    missing — set AIHUBMIX_API_KEY or pass --key <key>",
                 "[✗] KEY    未提供 — 设置环境变量 AIHUBMIX_API_KEY 或传 --key <key>"))
        print(_t("\nResult: FAIL. No API key available.", "\n结论: 失败。没有可用的 API key。"))
        return 1
    print(_t("[✓] KEY    provided", "[✓] KEY    已提供"))

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "aihubmixApi-skill/0.1",
    }

    # The public /v1/models list does NOT require auth, so it cannot validate a
    # key. Only a real chat call can — use a tiny one as the auth + text probe.
    probe_model = args.model or "gpt-4o-mini"
    payload = {"model": probe_model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 8, "temperature": 0}
    status, body = _http_request(f"{base}/chat/completions", method="POST", headers=headers, body=payload, timeout=timeout)
    reply = _extract_chat_reply(body) if status == 200 else None
    if reply is not None:
        note = "" if args.model else _t(" (probe model gpt-4o-mini)", "（探测模型 gpt-4o-mini）")
        print(_t(f"[✓] AUTH   key valid, {probe_model} call OK{note} → {reply[:60]!r}",
                 f"[✓] AUTH   key 有效，{probe_model} 调用成功{note} → {reply[:60]!r}"))
    elif status == 402 or _looks_like_balance_error(body):
        print(_t(f"[✗] BILLING key valid but insufficient balance/quota — HTTP {status}: {_redact(body, key)[:300]}",
                 f"[✗] 余额   key 有效但余额/额度不足 — HTTP {status}: {_redact(body, key)[:300]}"))
        print(_t("\nResult: FAIL (billing). The key works; the account needs a top-up.",
                 "\n结论: 失败（计费）。key 本身可用，但账户需要充值。"))
        return 1
    elif status in (401, 403) or _looks_like_auth_error(body):
        print(_t(f"[✗] AUTH   invalid key / no permission — HTTP {status}: {_redact(body, key)[:300]}",
                 f"[✗] AUTH   key 无效/无权限 — HTTP {status}: {_redact(body, key)[:300]}"))
        print(_t("\nResult: FAIL. Check the key is correct, enabled, and funded.",
                 "\n结论: 失败。请检查 key 是否正确、已启用、有余额。"))
        return 1
    else:
        info = f"HTTP {status}" if status else _t("network unreachable", "网络不可达")
        print(_t(f"[⚠] AUTH   unconfirmed — probing with {probe_model} returned {info}: {_redact(body, key)[:200]}",
                 f"[⚠] AUTH   未能确认 — 用 {probe_model} 探测返回 {info}: {_redact(body, key)[:200]}"))
        print(_t("           Usually the model is not available to your key (key likely fine); retry with --model <a model you can access>.",
                 "           多半是该模型对你的 key 不可用，而非 key 失效；用 --model <你有权限的模型> 重测。"))
        print(_t("\nResult: NOT PASSED (could not confirm key). Retry with --model <available model>.",
                 "\n结论: 未通过（无法确认 key）。建议用 --model 指定可用模型重测。"))
        return 1

    overall_ok = True

    if args.image:
        if not args.model:
            print(_t("[–] IMAGE  skipped (image probe needs --model <id>; you/the LLM pick which vision model)",
                     "[–] IMAGE  跳过（图片实测需要 --model <id>；该测哪个视觉模型由你/LLM 决定）"))
        else:
            payload = {
                "model": args.model,
                "max_tokens": 16,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What is the dominant color of this image? Answer with one word."},
                            {"type": "image_url", "image_url": {"url": _solid_png_data_url()}},
                        ],
                    }
                ],
            }
            status, body = _http_request(f"{base}/chat/completions", method="POST", headers=headers, body=payload, timeout=timeout)
            reply = _extract_chat_reply(body) if status == 200 else None
            if reply is not None:
                print(_t(f"[✓] IMAGE  {args.model} accepts image input → {reply[:60]!r}",
                         f"[✓] IMAGE  {args.model} 接受图片输入 → {reply[:60]!r}"))
            else:
                overall_ok = False
                print(_t(f"[✗] IMAGE  {args.model} no image support or call failed — HTTP {status}: {_redact(body, key)[:300]}",
                         f"[✗] IMAGE  {args.model} 不支持图片或调用失败 — HTTP {status}: {_redact(body, key)[:300]}"))

    print()
    if overall_ok:
        tail = (
            _t("Tested capabilities all OK.", "已实测的能力均正常。")
            if args.model
            else _t("Key valid; add --model <id> (and --image) to test a specific model.",
                    "key 有效；加 --model <id>（可再加 --image）可实测具体模型。")
        )
        print(_t(f"Result: PASS. {tail}", f"结论: 通过。{tail}"))
        return 0
    print(_t("Result: some checks did not pass — see the [✗] items above.",
             "结论: 部分检查未通过，见上面的 [✗] 项。"))
    return 1


# Categories that cannot accept chat input, dropped from input-modality
# candidate ranges (e.g. vision) even when the noisy modality field tags them.
_NON_CHAT_RE = re.compile(
    r"(embed|rerank|\bbge\b|\bbce\b|\bgte\b|\bm3e\b|jina|moderation|"
    r"whisper|\btts\b|text-to-speech|speech|transcrib|"
    r"flux|stable-diffusion|\bsdxl\b|dall-?e|midjourney|imagen|gpt-image|qwen-image|"
    r"seedream|seededit|kolors|cogview|ideogram|recraft|hunyuan-image|"
    r"\bveo\b|sora|kling|runway|video|hailuo|seedance|vidu)",
    re.IGNORECASE,
)


def _is_non_chat(model: dict[str, Any]) -> bool:
    """Drop models that cannot accept chat input (embeddings, generation, audio, video)."""
    if suggested_protocol(model) in {
        "embeddings", "images", "videos", "moderations",
        "audio-speech", "audio-transcriptions", "audio-translations",
    }:
        return True
    return bool(_NON_CHAT_RE.search(f"{model_id(model)} {model_label(model)}"))


# Capability discovery is deliberately broad + heuristic. Each spec scores a
# model by up to three signals and the caller/LLM picks from the range:
#   protocol: suggested_protocol(model) lands in the capability's endpoint set
#   modality: the model's metadata text contains a capability keyword
#   family:   the model id/name matches a known family regex
# protocol/family are treated as reliable; modality-only is noisy. The tool
# never picks a default and never asserts a hard capability fact.
CAPABILITY_SPECS: dict[str, dict[str, Any]] = {
    "vision": {
        "label": "图片输入 / 看图（chat 模型接受图片）",
        "aliases": ["image-input", "multimodal", "mm", "vlm", "看图", "图片输入", "多模态"],
        "protocols": None,
        "modality_tokens": ["image", "vision", "multimodal", "visual"],
        "require_chat": True,
        "family": (
            r"gpt-4o|gpt-4\.1|gpt-4-vision|gpt-4-turbo|gpt-5|chatgpt-4o|o1|o3|o4-mini|"
            r"gemini|claude-3|claude-4|claude-sonnet|claude-opus|claude-haiku|"
            r"qwen[\w.-]*vl|qwen-vl|glm-4v|glm-[\d.]+v|cogvlm|cogagent|yi-vision|yi-vl|"
            r"step-1v|step-1o|step-3|internvl|llava|pixtral|moondream|"
            r"llama[\w.-]*vision|grok[\w.-]*vision|grok-2-vision|grok-4|"
            r"doubao[\w.-]*vision|ernie[\w.-]*vl|minicpm-v|nova-lite|nova-pro|"
            r"phi-3[\w.-]*vision|phi-4[\w.-]*multimodal|kimi[\w.-]*vl|kimi-latest|moonshot[\w.-]*vl|"
            r"mistral-small-3|molmo|deepseek-vl"
        ),
    },
    "image-gen": {
        "label": "图像生成 / 文生图（text-to-image）",
        "aliases": ["t2i", "image-generation", "imagegen", "生图", "文生图", "画图"],
        "protocols": {"images"},
        "modality_tokens": ["image_generation", "text-to-image"],
        "require_chat": False,
        "family": (
            r"flux|kontext|stable-diffusion|\bsd3\b|\bsdxl\b|dall-?e|midjourney|\bmj\b|"
            r"imagen|gpt-image|qwen-image|hunyuan-image|hidream|seedream|seededit|kolors|"
            r"cogview|ideogram|recraft|wanx|gemini[\w.-]*image|nano-banana|grok[\w.-]*image|playground-v"
        ),
    },
    "video": {
        "label": "视频生成（text/image-to-video）",
        "aliases": ["t2v", "video-generation", "生视频", "文生视频", "视频"],
        "protocols": {"videos"},
        "modality_tokens": ["video"],
        "require_chat": False,
        "family": (
            r"veo|sora|kling|runway|gen-?3|hailuo|minimax[\w.-]*video|seedance|vidu|"
            r"wan[\w.-]*|cogvideo|pika|luma|dream-machine|ray-?2|pixverse|mochi|\bltx\b"
        ),
    },
    "audio-tts": {
        "label": "语音合成（文字转语音 TTS）",
        "aliases": ["tts", "text-to-speech", "speech", "语音合成"],
        "protocols": {"audio-speech"},
        "modality_tokens": ["speech", "text-to-speech", "tts"],
        "require_chat": False,
        "family": (
            r"\btts\b|text-to-speech|speech-0|cosyvoice|fish[\w.-]*audio|elevenlabs|"
            r"gpt-4o[\w.-]*tts|qwen[\w.-]*tts|doubao[\w.-]*tts|minimax[\w.-]*speech|index-tts"
        ),
    },
    "audio-stt": {
        "label": "语音识别 / 转写（STT/ASR）",
        "aliases": ["stt", "asr", "transcription", "whisper", "语音识别", "转写"],
        "protocols": {"audio-transcriptions", "audio-translations"},
        "modality_tokens": ["transcription", "translation"],
        "require_chat": False,
        "family": (
            r"whisper|transcrib|gpt-4o[\w.-]*transcribe|qwen[\w.-]*audio|sensevoice|paraformer|fun-?asr"
        ),
    },
    "embedding": {
        "label": "向量嵌入（embedding）",
        "aliases": ["embed", "embeddings", "向量", "嵌入"],
        "protocols": {"embeddings"},
        "modality_tokens": ["embedding"],
        "require_chat": False,
        "exclude": r"rerank",
        "family": (
            r"embed|text-embedding|\bbge\b|bge-[\w.-]+|\bbce\b|\bgte\b|\bm3e\b|jina[\w.-]*embed|"
            r"nomic[\w.-]*embed|qwen[\w.-]*embedding|conan-embedding|doubao[\w.-]*embedding|\bgme\b"
        ),
    },
    "rerank": {
        "label": "重排（rerank）",
        "aliases": ["reranker", "重排"],
        "protocols": None,
        "modality_tokens": ["rerank"],
        "require_chat": False,
        "family": r"rerank|reranker|bge[\w.-]*rerank|bce[\w.-]*rerank|jina[\w.-]*rerank|qwen3?-?rerank",
    },
}

for _spec in CAPABILITY_SPECS.values():
    _spec["_family_re"] = re.compile(_spec["family"], re.IGNORECASE)
    _spec["_exclude_re"] = re.compile(_spec["exclude"], re.IGNORECASE) if _spec.get("exclude") else None


def resolve_capability(name: str | None) -> str:
    key = (name or "vision").strip().lower()
    if key in CAPABILITY_SPECS:
        return key
    for cap, spec in CAPABILITY_SPECS.items():
        if key in [alias.lower() for alias in spec["aliases"]]:
            return cap
    raise SystemExit(f"未知能力: {name}。可选: {', '.join(CAPABILITY_SPECS)}")


def _capability_signals(model: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    if spec["protocols"] and suggested_protocol(model) in spec["protocols"]:
        signals.append("protocol")
    cap_text = " ".join(
        compact(model.get(key))
        for key in ("features", "capabilities", "input_modalities", "modality", "modalities", "types", "type", "endpoints")
        if model.get(key) is not None
    ).lower()
    if any(token in cap_text for token in spec["modality_tokens"]):
        signals.append("modality")
    if spec["_family_re"].search(f"{model_id(model)} {model_label(model)}"):
        signals.append("family")
    return signals


# --- Companion aihubmix CLI helpers (account data; opt-in only) -------------


def _find_aihubmix() -> str | None:
    """Locate the companion aihubmix CLI on PATH or known install locations."""
    found = shutil.which(CLI_BIN)
    if found:
        return found
    candidates: list[Path] = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "aihubmix" / "bin" / "aihubmix.exe")
    home = Path.home()
    candidates += [home / ".local" / "bin" / CLI_BIN, Path("/usr/local/bin") / CLI_BIN]
    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    return None


def _install_aihubmix() -> bool:
    """Run the official per-OS installer (explicit / opt-in only). Returns success."""
    if platform.system().lower().startswith("win"):
        cmd = ["powershell", "-NoProfile", "-Command", f"irm {CLI_INSTALL_PS1} | iex"]
    else:
        cmd = ["sh", "-c", f"curl -fsSL {CLI_INSTALL_SH} | sh"]
    try:
        return subprocess.run(cmd, timeout=300).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def cmd_install_cli(args: argparse.Namespace) -> int:
    existing = _find_aihubmix()
    if existing and not args.force:
        print(_t(f"aihubmix CLI already installed: {existing}", f"aihubmix CLI 已安装：{existing}"))
        print(_t(f"Project: {CLI_REPO_URL}", f"项目主页：{CLI_REPO_URL}"))
        return 0
    print(_t(f"Installing the aihubmix CLI (project: {CLI_REPO_URL}) ...",
             f"正在安装 aihubmix CLI（项目主页：{CLI_REPO_URL}）..."))
    if _install_aihubmix() and _find_aihubmix():
        print(_t("Done. Next: run `aihubmix login` to authenticate.",
                 "完成。下一步：运行 `aihubmix login` 登录。"))
        return 0
    print(_t(f"Install failed. Install manually — see {CLI_REPO_URL}",
             f"安装失败。请手动安装，见 {CLI_REPO_URL}"))
    return 1


def _my_callable_models(auto_install: bool = False) -> set[str]:
    """Lowercased ids the user's token can actually call (`aihubmix models list -j`)."""
    exe = _find_aihubmix()
    if not exe and auto_install:
        print(_t("aihubmix CLI not found; installing (--auto-install) ...",
                 "未找到 aihubmix CLI，正在自动安装（--auto-install）..."), file=sys.stderr)
        if _install_aihubmix():
            exe = _find_aihubmix()
    if not exe:
        raise SystemExit(_t(
            f"--mine needs the aihubmix CLI. Run `install-cli` (or add --auto-install). Project: {CLI_REPO_URL}",
            f"--mine 需要 aihubmix CLI。先运行 `install-cli`（或加 --auto-install）。项目主页：{CLI_REPO_URL}"))
    try:
        result = subprocess.run([exe, "models", "list", "-j"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"`aihubmix models list` failed: {exc}")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if "未登录" in detail or "login" in detail.lower() or "token" in detail.lower():
            raise SystemExit(_t(
                f"Not logged in. Run `aihubmix login` first, or drop --mine. Project: {CLI_REPO_URL}",
                f"尚未登录。请先 `aihubmix login`，或去掉 --mine。项目主页：{CLI_REPO_URL}"))
        raise SystemExit(f"`aihubmix models list` error: {detail[:200]}")
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise SystemExit("could not parse `aihubmix models list -j` output")
    rows = data.get("data") if isinstance(data, dict) else data
    return {
        str(row.get("model")).strip().lower()
        for row in (rows or [])
        if isinstance(row, dict) and row.get("model")
    }


def cmd_candidates(args: argparse.Namespace) -> None:
    cap = resolve_capability(getattr(args, "capability", None))
    spec = CAPABILITY_SPECS[cap]
    models = extract_models(load_json_source(args.source))

    mine = None
    if getattr(args, "mine", False):
        mine = _my_callable_models(auto_install=getattr(args, "auto_install", False))

    picked: list[tuple[dict[str, Any], bool, str]] = []
    for item in models:
        if spec["require_chat"] and _is_non_chat(item):
            continue
        exclude_re = spec.get("_exclude_re")
        if exclude_re and exclude_re.search(f"{model_id(item)} {model_label(item)}"):
            continue
        if mine is not None and model_id(item).strip().lower() not in mine:
            continue  # keep only models the user's token can actually call
        signals = _capability_signals(item, spec)
        if not signals:
            continue
        strong = ("protocol" in signals) or ("family" in signals)
        picked.append((item, strong, "+".join(signals)))
    # Reliable protocol/family matches first, then noisier modality-only ones.
    picked.sort(key=lambda row: (0 if row[1] else 1, model_id(row[0]).lower()))
    selected = [(item, signal) for item, _strong, signal in picked[: args.limit]]

    if args.json:
        print(json.dumps(
            [
                {
                    "capability": cap,
                    "mine": mine is not None,
                    "model_id": model_id(item),
                    "name": model_label(item),
                    "signal": signal,
                    "features": features(item),
                    "context": context_display(item),
                }
                for item, signal in selected
            ],
            ensure_ascii=False,
            indent=2,
        ))
        return

    mine_en = " callable by your token" if mine is not None else ""
    mine_zh = "（已按你的 token 可调过滤）" if mine is not None else ""
    print(_t(
        f"AIHubMix candidate models for capability '{cap}'{mine_en} (broad heuristic: protocol / family / modality; no default picked)",
        f"AIHubMix【{spec['label']}】候选模型{mine_zh}（宽口径启发式：协议 / 家族名 / modality 字段；不替你挑默认）",
    ))
    if mine is not None and not selected:
        print(_t(
            f"\nNone of the '{cap}' candidates are callable by your token. Try without --mine, or check `aihubmix models list`.",
            f"\n你的 token 在【{cap}】下没有可调候选。可去掉 --mine，或查 `aihubmix models list`。",
        ))
        return
    print(_t(
        "Note: a candidate is not a guarantee; pick per task (you/the LLM), then confirm with `doctor`.",
        "注意：候选不等于确定可用；请由调用方/LLM 按任务从中挑选，再用 `doctor` 实测确认。",
    ))
    print()
    rows = [
        [model_id(item), model_label(item), signal, features(item) or "-", context_display(item)]
        for item, signal in selected
    ]
    print_table(["model_id", "name", "signal", "features/modalities", "context"], rows)
    mine_foot_en = " | filtered to your token" if mine is not None else ""
    mine_foot_zh = " | 已按你的 token 过滤" if mine is not None else ""
    print(_t(
        f"\ncapability: {cap} | {len(selected)} candidates{mine_foot_en} | source: {display_models_source()}",
        f"\n能力: {cap} | 共 {len(selected)} 个候选{mine_foot_zh} | source: {display_models_source()}",
    ))
    print(_t(
        "signal: protocol=endpoint type; family=known family name (both reliable); modality=metadata keyword only (noisy, verify).",
        "signal: protocol=接口类型匹配；family=按已知家族名匹配（均较可靠）；modality=仅元数据出现关键词（噪声大，需实测）。",
    ))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query AIHubMix models and API contract helpers.")
    parser.add_argument(
        "--lang", choices=["en", "zh"],
        help="Output language for status lines/labels (default: env AIHUBMIX_LANG or en).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List models from the models API.")
    list_parser.add_argument("--source", help="Models JSON URL, local JSON file, or '-' for stdin.")
    list_parser.add_argument("--query", help="Filter models by substring.")
    list_parser.add_argument("--limit", type=int, default=50)
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(func=cmd_list)

    get_parser = subparsers.add_parser("get", help="Show one model by ID or substring.")
    get_parser.add_argument("model")
    get_parser.add_argument("--source")
    get_parser.add_argument("--json", action="store_true")
    get_parser.set_defaults(func=cmd_get)

    compare_parser = subparsers.add_parser("compare", help="Compare pricing and context for models.")
    compare_parser.add_argument("models", nargs="+")
    compare_parser.add_argument("--source")
    compare_parser.add_argument("--json", action="store_true")
    compare_parser.set_defaults(func=cmd_compare)

    latest_parser = subparsers.add_parser("latest-report", help="Report the first N models with pricing, context, and an example.")
    latest_parser.add_argument("--source", help="Models JSON URL, local JSON file, or '-' for stdin.")
    latest_parser.add_argument("--limit", type=int, default=5)
    latest_parser.add_argument("--os", choices=["auto", "windows", "mac", "linux"], default="auto")
    latest_parser.set_defaults(func=cmd_latest_report)

    report_parser = subparsers.add_parser("report", help="Report models matching a query with pricing, context, endpoint, and examples.")
    report_parser.add_argument("query")
    report_parser.add_argument("--source", help="Models JSON URL, local JSON file, or '-' for stdin.")
    report_parser.add_argument("--limit", type=int, default=20)
    report_parser.add_argument("--os", choices=["auto", "windows", "mac", "linux"], default="auto")
    report_parser.set_defaults(func=cmd_report)

    protocols_parser = subparsers.add_parser("protocols", help="Summarize live aihubmix OpenAPI operations (remote).")
    protocols_parser.add_argument("--json", action="store_true")
    protocols_parser.set_defaults(func=cmd_protocols)

    error_contract_parser = subparsers.add_parser("error-contract", help="Summarize the GatewayError contract from the live OpenAPI spec (remote).")
    error_contract_parser.add_argument("--json", action="store_true")
    error_contract_parser.set_defaults(func=cmd_error_contract)

    sdk_parser = subparsers.add_parser("sdk-check", help="Check @aihubmix/ai-sdk-provider version without installing or updating it.")
    sdk_parser.add_argument("--project", help="Project directory to search for node_modules.")
    sdk_parser.add_argument("--version", help="Target SDK version to compare against.")
    sdk_parser.add_argument("--offline", action="store_true", help="Skip npm registry latest-version check.")
    sdk_parser.set_defaults(func=cmd_sdk_check)

    sdk_info_parser = subparsers.add_parser("sdk-info", help="Summarize @aihubmix/ai-sdk-provider capabilities and auth/routing defaults.")
    sdk_info_parser.add_argument("--project", help="Project directory to search for installed node_modules.")
    sdk_info_parser.add_argument("--package-dir", help="Path to an unpacked @aihubmix/ai-sdk-provider package directory.")
    sdk_info_parser.add_argument("--version", default=SDK_RECOMMENDED_VERSION, help="SDK version to inspect from npm when no package is installed.")
    sdk_info_parser.add_argument(
        "--source",
        choices=["auto", "installed", "npm"],
        default="auto",
        help="SDK metadata source. npm reads the package tarball from the npm registry.",
    )
    sdk_info_parser.add_argument("--json", action="store_true")
    sdk_info_parser.set_defaults(func=cmd_sdk_info)

    example_parser = subparsers.add_parser("example", help="Generate minimal API call examples.")
    example_parser.add_argument(
        "protocol",
        choices=sorted([*PROTOCOL_SPECS.keys(), *PROTOCOL_ALIASES.keys()]),
        help="Protocol or endpoint shape to generate.",
    )
    example_parser.add_argument("--model", required=True)
    example_parser.add_argument("--lang", choices=["both", "curl", "python", "js", "json"], default="both")
    example_parser.add_argument("--os", choices=["auto", "windows", "mac", "linux"], default="auto")
    example_parser.set_defaults(func=cmd_example)

    troubleshoot_parser = subparsers.add_parser("troubleshoot", help="Explain common API failure checks.")
    troubleshoot_parser.add_argument("--status", type=int)
    troubleshoot_parser.add_argument("--body", help="JSON error body string.")
    troubleshoot_parser.add_argument("--body-file", help="Path to a JSON error body.")
    troubleshoot_parser.add_argument("--endpoint")
    troubleshoot_parser.add_argument("--model")
    troubleshoot_parser.add_argument("--request-id")
    troubleshoot_parser.add_argument("--contract", action="store_true", help="Also fetch the live GatewayError contract (remote) and show a match.")
    troubleshoot_parser.set_defaults(func=cmd_troubleshoot)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Preflight an AIHubMix key: verify auth, then optionally smoke-test text and image input on a chosen model.",
    )
    doctor_parser.add_argument("--key", help="API key. Defaults to env AIHUBMIX_API_KEY. Never printed in full.")
    doctor_parser.add_argument("--base-url", help="OpenAI-compatible base. Defaults to env AIHUBMIX_BASE_URL or https://aihubmix.com/v1.")
    doctor_parser.add_argument("--model", help="Model id to smoke-test (text; also image with --image).")
    doctor_parser.add_argument("--image", action="store_true", help="Also probe image input on --model.")
    doctor_parser.add_argument("--timeout", type=float, default=30)
    doctor_parser.set_defaults(func=cmd_doctor)

    candidates_parser = subparsers.add_parser(
        "candidates",
        help="List a BROAD candidate range for a capability (vision/image-gen/video/audio-tts/audio-stt/embedding/rerank); caller/LLM picks, tool chooses no default.",
    )
    candidates_parser.add_argument(
        "--capability", "-c", required=True,
        help="Capability or alias. One of: " + ", ".join(CAPABILITY_SPECS) + ".",
    )
    candidates_parser.add_argument("--source", help="Models JSON URL, local JSON file, or '-' for stdin.")
    candidates_parser.add_argument("--limit", type=int, default=40)
    candidates_parser.add_argument("--json", action="store_true")
    candidates_parser.add_argument("--mine", action="store_true", help="Filter to models your token can actually call (needs the aihubmix CLI + login).")
    candidates_parser.add_argument("--auto-install", action="store_true", help="With --mine: install the aihubmix CLI automatically if missing.")
    candidates_parser.set_defaults(func=cmd_candidates)

    vision_parser = subparsers.add_parser(
        "vision-candidates",
        help="Alias for `candidates --capability vision`.",
    )
    vision_parser.add_argument("--source", help="Models JSON URL, local JSON file, or '-' for stdin.")
    vision_parser.add_argument("--limit", type=int, default=40)
    vision_parser.add_argument("--json", action="store_true")
    vision_parser.add_argument("--mine", action="store_true", help="Filter to models your token can actually call.")
    vision_parser.add_argument("--auto-install", action="store_true", help="With --mine: install the aihubmix CLI automatically if missing.")
    vision_parser.set_defaults(func=cmd_candidates, capability="vision")

    install_cli_parser = subparsers.add_parser(
        "install-cli",
        help="Install the companion aihubmix CLI via its official per-OS installer.",
    )
    install_cli_parser.add_argument("--force", action="store_true", help="Reinstall even if already present.")
    install_cli_parser.set_defaults(func=cmd_install_cli)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    global _LANG
    _LANG = (args.lang or os.environ.get("AIHUBMIX_LANG") or "en").strip().lower()
    if _LANG not in ("en", "zh"):
        _LANG = "en"
    result = args.func(args)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
