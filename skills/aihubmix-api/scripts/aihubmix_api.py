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
import sys
import tarfile
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


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


def display_models_source() -> str:
    return DEFAULT_MODELS_URL


def display_openapi_source(filename: str = "openapi.json") -> str:
    if filename == "openapi.json":
        return OPENAPI_JSON_URL
    if filename == "contract.json":
        return CONTRACT_JSON_URL
    return OPENAPI_REPO_URL


def display_error_contract_source() -> str:
    return GATEWAY_ERRORS_URL


def load_json_source(source: str | None) -> Any:
    source = source or os.environ.get("AIHUBMIX_MODELS_URL") or DEFAULT_MODELS_URL
    if source == "-":
        return json.load(sys.stdin)
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(
            source,
            headers={
                "Accept": "application/json",
                "User-Agent": "aihubmix-api-skill/0.1",
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
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} (本地时间，{offset_label})"


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
    if any(value in raw_endpoint or value in raw_type for value in ("embedding", "image", "audio", "speech", "transcription", "video")):
        return None
    if "llm" in raw_type or "chat" in raw_type:
        return "chat"
    if any(value in searchable for value in ("gemini", "claude", "anthropic")):
        if "gemini" in searchable:
            return "gemini"
        return "messages"
    return "chat"


def protocol_name(protocol: str) -> str:
    labels = {
        "chat": "OpenAI-Compatible Chat",
        "responses": "OpenAI Responses",
        "messages": "Claude/Anthropic-Compatible Messages",
        "gemini": "Gemini Native",
    }
    return labels[protocol]


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


def repo_candidates(explicit: str | None = None) -> list[Path]:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_repo = os.environ.get("AIHUBMIX_OPENAPI_REPO")
    if env_repo:
        candidates.append(Path(env_repo).expanduser())
    cwd = Path.cwd()
    for path in [cwd, *cwd.parents]:
        candidates.append(path / "aihubmix-openapi")
    candidates.append(Path.home() / "aihubmix-openapi")
    unique = []
    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        if str(resolved).lower() not in seen:
            unique.append(candidate)
            seen.add(str(resolved).lower())
    return unique


def find_openapi_file(repo: str | None = None, filename: str = "openapi.json") -> Path | None:
    for candidate in repo_candidates(repo):
        path = candidate / filename
        if path.exists():
            return path
    return None


def load_openapi(repo: str | None = None, filename: str = "openapi.json") -> tuple[dict[str, Any] | None, Path | None]:
    path = find_openapi_file(repo, filename)
    if not path:
        return None, None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle), path


def find_gateway_file(repo: str | None = None, filename: str = "errors.yml") -> Path | None:
    for candidate in repo_candidates(repo):
        path = candidate / "gateway" / filename
        if path.exists():
            return path
    return None


def load_error_contract(repo: str | None = None) -> tuple[dict[str, Any], Path]:
    path = find_gateway_file(repo, "errors.yml")
    if not path:
        raise SystemExit(
            "Could not find aihubmix-openapi/gateway/errors.yml. Set AIHUBMIX_OPENAPI_REPO or pass --repo."
        )
    text = path.read_text(encoding="utf-8")
    statuses: dict[str, dict[str, str]] = {}
    current_status: str | None = None
    for line in text.splitlines():
        status_match = re.match(r'\s{4}"?([0-9]{3}|5XX)"?:\s*$', line)
        if status_match:
            current_status = status_match.group(1)
            statuses[current_status] = {}
            continue
        if current_status:
            description_match = re.match(r"\s{6}description:\s*(.+?)\s*$", line)
            if description_match:
                statuses[current_status]["description"] = description_match.group(1).strip().strip('"')
                continue
            ref_match = re.search(r'\$ref:\s*"?([^"}\s]+)', line)
            if ref_match:
                statuses[current_status]["schema"] = ref_match.group(1).strip()

    return {
        "source": str(path),
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
        "statuses": statuses,
    }, path


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
    spec, path = load_openapi(args.repo)
    if not spec:
        raise SystemExit(
            "Could not find aihubmix-openapi/openapi.json. Set AIHUBMIX_OPENAPI_REPO or pass --repo."
        )
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
    contract, path = load_error_contract(args.repo)
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
            "User-Agent": "aihubmix-api-skill/0.1",
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
        headers={"User-Agent": "aihubmix-api-skill/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} while fetching {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not fetch {url}: {exc.reason}") from exc


def sdk_baseline_metadata(version: str = SDK_RECOMMENDED_VERSION) -> dict[str, Any]:
    return {
        "source": f"baseline for {SDK_PACKAGE_NAME}@{version}",
        "package": SDK_PACKAGE_NAME,
        "version": version,
        "exports": ["aihubmix", "createAihubmix"],
        "provider_methods": [
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
        ],
        "tools": ["codeInterpreter", "fileSearch", "imageGeneration", "webSearchPreview", "webSearch"],
        "environment_variable": "AIHUBMIX_API_KEY",
        "base_urls": ["https://aihubmix.com/v1", "https://aihubmix.com/gemini/v1beta"],
        "headers": ["Authorization", "APP-Code", "Content-Type", "x-api-key", "x-goog-api-key"],
        "routing": [
            "Claude model IDs starting with claude- use Anthropic-compatible messages with x-api-key.",
            "Gemini or Imagen model IDs use Gemini native base URL unless suffixed with -nothink or -search.",
            "Other chat models use OpenAI-compatible chat through https://aihubmix.com/v1.",
        ],
    }


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
    if args.source == "baseline":
        return sdk_baseline_metadata(args.version or SDK_RECOMMENDED_VERSION)

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


def endpoint_path(protocol: str, model: str) -> str:
    if protocol == "chat":
        return "/v1/chat/completions"
    if protocol == "responses":
        return "/v1/responses"
    if protocol == "messages":
        return "/v1/messages"
    if protocol == "gemini":
        return f"/gemini/v1beta/models/{model}:generateContent"
    raise ValueError(protocol)


def example_payload(protocol: str, model: str) -> dict[str, Any]:
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
    raise ValueError(protocol)


def auth_header(protocol: str) -> tuple[str, str]:
    if protocol == "messages":
        return "x-api-key", "$AIHUBMIX_API_KEY"
    if protocol == "gemini":
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


def shell_response_parser() -> str:
    return (
        "import json,sys; d=json.load(sys.stdin); "
        "text=(d.get('output_text') or ((d.get('choices') or [{}])[0].get('message') or {}).get('content') "
        "or ((d.get('content') or [{}])[0]).get('text') "
        "or ((((d.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [{}])[0]).get('text')); "
        "print(text if text is not None else json.dumps(d, ensure_ascii=False))"
    )


def render_cmd_example(protocol: str, model: str, os_name: str) -> str:
    url = base_url() + endpoint_path(protocol, model)
    payload = example_payload(protocol, model)
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    header_name, _ = auth_header(protocol)

    if os_name == "windows":
        if protocol == "messages":
            auth_line = '"x-api-key" = $AIHUBMIX_API_KEY'
        elif protocol == "gemini":
            auth_line = '"x-goog-api-key" = $AIHUBMIX_API_KEY'
        else:
            auth_line = '"Authorization" = "Bearer $AIHUBMIX_API_KEY"'
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
            f"{powershell_response_printer()}\n"
            "# To inspect the full response, uncomment the next line:\n"
            "# $response | ConvertTo-Json -Depth 20"
        )

    if protocol == "messages":
        auth_arg = '-H "x-api-key: $AIHUBMIX_API_KEY"'
    elif protocol == "gemini":
        auth_arg = '-H "x-goog-api-key: $AIHUBMIX_API_KEY"'
    else:
        auth_arg = '-H "Authorization: Bearer $AIHUBMIX_API_KEY"'
    compact_payload = json.dumps(payload, ensure_ascii=False)
    return textwrap.dedent(
        f"""\
        read -rsp "Paste AIHubMix API Key: " AIHUBMIX_API_KEY; echo

        curl -s {json.dumps(url)} \\
          {auth_arg} \\
          -H "Content-Type: application/json" \\
          -d {json.dumps(compact_payload)} \\
          | python3 -c {json.dumps(shell_response_parser())}
        """
    ).strip()


def render_js_example(protocol: str, model: str) -> str:
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
    header_name, header_value = auth_header(protocol)
    header_value_js = (
        "process.env.AIHUBMIX_API_KEY"
        if protocol in {"messages", "gemini"}
        else '`Bearer ${process.env.AIHUBMIX_API_KEY}`'
    )
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    payload_lines = ["  body: JSON.stringify(" + payload_json.splitlines()[0]]
    payload_lines.extend("  " + line for line in payload_json.splitlines()[1:])
    payload_lines[-1] = payload_lines[-1] + "),"
    return "\n".join(
        [
            f'const response = await fetch("{base_url()}{path}", {{',
            '  method: "POST",',
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
            "  data.candidates?.[0]?.content?.parts?.[0]?.text;",
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
        if protocol != "chat":
            print("\n# Note: Python OpenAI SDK sample is for the OpenAI-shaped chat endpoint.")
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

    if args.repo:
        contract, path = load_error_contract(args.repo)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query AIHubMix models and API contract helpers.")
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

    protocols_parser = subparsers.add_parser("protocols", help="Summarize aihubmix-openapi operations.")
    protocols_parser.add_argument("--repo", help="Path to AIhubmix/aihubmix-openapi checkout.")
    protocols_parser.add_argument("--json", action="store_true")
    protocols_parser.set_defaults(func=cmd_protocols)

    error_contract_parser = subparsers.add_parser("error-contract", help="Summarize gateway/errors.yml GatewayError contract.")
    error_contract_parser.add_argument("--repo", help="Path to AIhubmix/aihubmix-openapi checkout.")
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
        choices=["auto", "installed", "npm", "baseline"],
        default="auto",
        help="SDK metadata source. baseline is offline and pinned to the recommended SDK surface.",
    )
    sdk_info_parser.add_argument("--json", action="store_true")
    sdk_info_parser.set_defaults(func=cmd_sdk_info)

    example_parser = subparsers.add_parser("example", help="Generate minimal API call examples.")
    example_parser.add_argument(
        "protocol",
        choices=["chat", "responses", "messages", "gemini"],
        help="Protocol shape to generate.",
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
    troubleshoot_parser.add_argument("--repo", help="Path to AIhubmix/aihubmix-openapi checkout for GatewayError contract matching.")
    troubleshoot_parser.set_defaults(func=cmd_troubleshoot)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
