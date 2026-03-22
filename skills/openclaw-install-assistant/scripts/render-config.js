#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

const PROVIDERS = {
  aihubmix: {
    profileId: "aihubmix:default",
    provider: "aihubmix",
    primaryModel: "aihubmix/claude-opus-4-6",
    openclawTemplate: "aihubmix-openclaw.template.json",
  },
  anthropic: {
    profileId: "anthropic:default",
    provider: "anthropic",
    primaryModel: "anthropic/claude-sonnet-4-5",
    openclawTemplate: "builtin-openclaw.template.json",
  },
  openai: {
    profileId: "openai:default",
    provider: "openai",
    primaryModel: "openai/gpt-4o",
    openclawTemplate: "builtin-openclaw.template.json",
  },
  google: {
    profileId: "google:default",
    provider: "google",
    primaryModel: "google/gemini-2.5-flash",
    openclawTemplate: "builtin-openclaw.template.json",
  },
  openrouter: {
    profileId: "openrouter:default",
    provider: "openrouter",
    primaryModel: "anthropic/claude-sonnet-4-5",
    openclawTemplate: "builtin-openclaw.template.json",
  },
};

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const key = arg.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
}

function usage() {
  console.error(
    [
      "Usage:",
      '  node scripts/render-config.js --provider <aihubmix|anthropic|openai|google|openrouter> --api-key "<key>" [--home <dir>] [--stdout]',
      "",
      "Examples:",
      '  node scripts/render-config.js --provider openai --api-key "<key>"',
      '  node scripts/render-config.js --provider aihubmix --api-key "<key>" --home "/tmp/openclaw-test"',
    ].join("\n"),
  );
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function replaceDeep(value, replacements) {
  if (typeof value === "string") {
    let next = value;
    for (const [from, to] of Object.entries(replacements)) {
      next = next.split(from).join(to);
    }
    return next;
  }
  if (Array.isArray(value)) {
    return value.map((item) => replaceDeep(item, replacements));
  }
  if (value && typeof value === "object") {
    const out = {};
    for (const [key, child] of Object.entries(value)) {
      const nextKey = replaceDeep(key, replacements);
      out[nextKey] = replaceDeep(child, replacements);
    }
    return out;
  }
  return value;
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help || args.h) {
    usage();
    process.exit(0);
  }

  const providerKey = String(args.provider || "").toLowerCase();
  const apiKey = args["api-key"];
  const homeDir = args.home || path.join(os.homedir(), ".openclaw");
  const stdout = Boolean(args.stdout);
  const provider = PROVIDERS[providerKey];

  if (!provider || !apiKey) {
    usage();
    process.exit(1);
  }

  const skillRoot = path.resolve(__dirname, "..");
  const assetsDir = path.join(skillRoot, "assets");

  const openclawTemplate = readJson(
    path.join(assetsDir, provider.openclawTemplate),
  );
  const authTemplate = readJson(path.join(assetsDir, "auth-profiles.template.json"));

  const replacements = {
    "__PROFILE_ID__": provider.profileId,
    "__PROVIDER__": provider.provider,
    "__PRIMARY_MODEL__": provider.primaryModel,
    "__API_KEY__": apiKey,
  };

  const openclawConfig = replaceDeep(openclawTemplate, replacements);
  const authProfiles = replaceDeep(authTemplate, replacements);

  if (stdout) {
    process.stdout.write(
      JSON.stringify(
        {
          openclawConfig,
          authProfiles,
        },
        null,
        2,
      ),
    );
    process.stdout.write("\n");
    return;
  }

  const openclawPath = path.join(homeDir, "openclaw.json");
  const authPath = path.join(homeDir, "agents", "main", "agent", "auth-profiles.json");

  writeJson(openclawPath, openclawConfig);
  writeJson(authPath, authProfiles);

  console.log(`Wrote ${openclawPath}`);
  console.log(`Wrote ${authPath}`);
  console.log(`Provider: ${provider.provider}`);
  console.log(`Primary model: ${provider.primaryModel}`);
}

main();
