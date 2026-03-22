# Provider 配置模板

在 OpenClaw 安装完成后，先检查是否已有配置，再按 provider 写入 `openclaw.json` 与 `auth-profiles.json`。

## 配置检查

### bash

```bash
test -f ~/.openclaw/openclaw.json && cat ~/.openclaw/openclaw.json | grep -c '"provider"' || echo "no config"
```

### Windows

```text
node -e "const fs=require('fs'),p=require('path'),h=require('os').homedir();const f=p.join(h,'.openclaw','openclaw.json');if(!fs.existsSync(f)){console.log('no config')}else{const c=fs.readFileSync(f,'utf8');const m=c.match(/\"provider\"/g);console.log('provider count: '+(m?m.length:0))}"
```

## API Key 页面

- AIhubmix: https://console.aihubmix.com/token
- Anthropic: https://console.anthropic.com/settings/keys
- OpenAI: https://platform.openai.com/api-keys
- Google: https://aistudio.google.com/apikey
- OpenRouter: https://openrouter.ai/keys

打开方式：macOS 用 `open`，Linux 用 `xdg-open`，Windows 用 `cmd /c start "" "URL"`。如果打不开，就把链接发给用户。

## 配置格式约束

- `auth.profiles` 是对象，不是数组
- `auth.order` 是对象，不是数组
- API Key 只写入 `~/.openclaw/agents/main/agent/auth-profiles.json`
- 不在 `openclaw.json` 中写 `credentials`、`apiKey`、`id` 等无效字段
- 选择 AIhubmix 时，必须包含 `models.providers.aihubmix`

## 静态模板文件

优先把 `assets/` 里的模板当作结构真源，再按当前 provider 替换占位符或写入命令：

- `assets/aihubmix-openclaw.template.json`
- `assets/builtin-openclaw.template.json`
- `assets/auth-profiles.template.json`

用途：

- 需要快速确认 JSON 结构时，直接查看模板
- 需要写 bash 或 Windows 命令时，以模板内容为准生成目标文件
- 需要排查“字段写错”时，先对照模板检查

## 辅助脚本

优先使用 `scripts/render-config.js` 生成配置文件，减少手写 JSON 出错概率。

示例：

```bash
node scripts/render-config.js --provider openai --api-key "用户提供的key"
```

AIhubmix：

```bash
node scripts/render-config.js --provider aihubmix --api-key "用户提供的key"
```

脚本默认写入：

- `~/.openclaw/openclaw.json`
- `~/.openclaw/agents/main/agent/auth-profiles.json`

如需先预览结构，不直接写文件：

```bash
node scripts/render-config.js --provider anthropic --api-key "用户提供的key" --stdout
```

如需写到测试目录：

```bash
node scripts/render-config.js --provider google --api-key "用户提供的key" --home "/tmp/openclaw-test"
```

## Provider 映射

| 服务商 | provider | profileId | model |
|--------|----------|-----------|-------|
| AIhubmix | aihubmix | aihubmix:default | aihubmix/claude-opus-4-6 |
| Anthropic | anthropic | anthropic:default | anthropic/claude-sonnet-4-5 |
| OpenAI | openai | openai:default | openai/gpt-4o |
| Google | google | google:default | google/gemini-2.5-flash |
| OpenRouter | openrouter | openrouter:default | anthropic/claude-sonnet-4-5 |

## AIhubmix bash 模板

对应静态模板：`assets/aihubmix-openclaw.template.json` + `assets/auth-profiles.template.json`

```bash
OPENCLAW_API_KEY="用户提供的key" && mkdir -p ~/.openclaw ~/.openclaw/agents/main/agent && cat > ~/.openclaw/openclaw.json << 'EOF'
{
  "auth": {
    "profiles": {
      "aihubmix:default": {
        "provider": "aihubmix",
        "mode": "api_key"
      }
    },
    "order": {
      "default": ["aihubmix:default"]
    }
  },
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace",
      "model": {
        "primary": "aihubmix/claude-opus-4-6"
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "aihubmix": {
        "baseUrl": "https://aihubmix.com",
        "api": "anthropic-messages",
        "models": [
          { "id": "claude-opus-4-6", "name": "claude-opus-4-6", "contextWindow": 128000 },
          { "id": "claude-sonnet-4-5-20250514", "name": "claude-sonnet-4-5-20250514", "contextWindow": 128000 },
          { "id": "gpt-5", "name": "gpt-5", "contextWindow": 128000 },
          { "id": "gpt-5-mini", "name": "gpt-5-mini", "contextWindow": 128000 },
          { "id": "gpt-4.1", "name": "gpt-4.1", "contextWindow": 128000 },
          { "id": "gpt-4o", "name": "gpt-4o", "contextWindow": 128000 },
          { "id": "o3", "name": "o3", "contextWindow": 128000 },
          { "id": "o4-mini", "name": "o4-mini", "contextWindow": 128000 },
          { "id": "DeepSeek-V3", "name": "DeepSeek-V3", "contextWindow": 128000 },
          { "id": "DeepSeek-R1", "name": "DeepSeek-R1", "contextWindow": 128000 },
          { "id": "gemini-2.5-pro", "name": "gemini-2.5-pro", "contextWindow": 128000 },
          { "id": "gemini-2.5-flash", "name": "gemini-2.5-flash", "contextWindow": 128000 },
          { "id": "gemini-3-pro-preview", "name": "gemini-3-pro-preview", "contextWindow": 128000 },
          { "id": "gemini-3-flash-preview", "name": "gemini-3-flash-preview", "contextWindow": 128000 },
          { "id": "Qwen3-235B-A22B-Instruct-2507", "name": "Qwen3-235B-A22B-Instruct-2507", "contextWindow": 128000 },
          { "id": "kimi-k2-0711-preview", "name": "kimi-k2-0711-preview", "contextWindow": 128000 }
        ]
      }
    }
  },
  "gateway": {
    "port": 18789,
    "bind": "loopback",
    "auth": {
      "mode": "token"
    },
    "mode": "local"
  }
}
EOF
cat > ~/.openclaw/agents/main/agent/auth-profiles.json << EOF
{
  "version": 1,
  "profiles": {
    "aihubmix:default": {
      "type": "api_key",
      "provider": "aihubmix",
      "key": "$OPENCLAW_API_KEY"
    }
  }
}
EOF
chmod 600 ~/.openclaw/openclaw.json ~/.openclaw/agents/main/agent/auth-profiles.json
```

## 内置 provider bash 模板

将 `PROFILEID`、`PROVIDER`、`MODEL` 替换为实际值：

对应静态模板：`assets/builtin-openclaw.template.json` + `assets/auth-profiles.template.json`

```bash
OPENCLAW_API_KEY="用户提供的key" && mkdir -p ~/.openclaw ~/.openclaw/agents/main/agent && cat > ~/.openclaw/openclaw.json << 'EOF'
{
  "auth": {
    "profiles": {
      "PROFILEID": {
        "provider": "PROVIDER",
        "mode": "api_key"
      }
    },
    "order": {
      "default": ["PROFILEID"]
    }
  },
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace",
      "model": {
        "primary": "PROVIDER/MODEL"
      }
    }
  },
  "gateway": {
    "port": 18789,
    "bind": "loopback",
    "auth": {
      "mode": "token"
    },
    "mode": "local"
  }
}
EOF
cat > ~/.openclaw/agents/main/agent/auth-profiles.json << EOF
{
  "version": 1,
  "profiles": {
    "PROFILEID": {
      "type": "api_key",
      "provider": "PROVIDER",
      "key": "$OPENCLAW_API_KEY"
    }
  }
}
EOF
chmod 600 ~/.openclaw/openclaw.json ~/.openclaw/agents/main/agent/auth-profiles.json
```

## Windows 模板

### AIhubmix `openclaw.json`

```text
node -e "const fs=require('fs'),p=require('path'),h=require('os').homedir();const d=p.join(h,'.openclaw');fs.mkdirSync(d,{recursive:true});const config={auth:{profiles:{'aihubmix:default':{provider:'aihubmix',mode:'api_key'}},order:{default:['aihubmix:default']}},agents:{defaults:{workspace:'~/.openclaw/workspace',model:{primary:'aihubmix/claude-opus-4-6'}}},models:{mode:'merge',providers:{aihubmix:{baseUrl:'https://aihubmix.com',api:'anthropic-messages',models:[{id:'claude-opus-4-6',name:'claude-opus-4-6',contextWindow:128000},{id:'claude-sonnet-4-5-20250514',name:'claude-sonnet-4-5-20250514',contextWindow:128000},{id:'gpt-5',name:'gpt-5',contextWindow:128000},{id:'gpt-5-mini',name:'gpt-5-mini',contextWindow:128000},{id:'gpt-4.1',name:'gpt-4.1',contextWindow:128000},{id:'gpt-4o',name:'gpt-4o',contextWindow:128000},{id:'o3',name:'o3',contextWindow:128000},{id:'o4-mini',name:'o4-mini',contextWindow:128000},{id:'DeepSeek-V3',name:'DeepSeek-V3',contextWindow:128000},{id:'DeepSeek-R1',name:'DeepSeek-R1',contextWindow:128000},{id:'gemini-2.5-pro',name:'gemini-2.5-pro',contextWindow:128000},{id:'gemini-2.5-flash',name:'gemini-2.5-flash',contextWindow:128000},{id:'gemini-3-pro-preview',name:'gemini-3-pro-preview',contextWindow:128000},{id:'gemini-3-flash-preview',name:'gemini-3-flash-preview',contextWindow:128000},{id:'Qwen3-235B-A22B-Instruct-2507',name:'Qwen3-235B-A22B-Instruct-2507',contextWindow:128000},{id:'kimi-k2-0711-preview',name:'kimi-k2-0711-preview',contextWindow:128000}]}}},gateway:{port:18789,bind:'loopback',auth:{mode:'token'},mode:'local'}};fs.writeFileSync(p.join(d,'openclaw.json'),JSON.stringify(config,null,2));console.log('openclaw.json written')"
```

### 内置 provider `openclaw.json`

```text
node -e "const fs=require('fs'),p=require('path'),h=require('os').homedir();const d=p.join(h,'.openclaw');fs.mkdirSync(d,{recursive:true});const config={auth:{profiles:{'PROFILEID':{provider:'PROVIDER',mode:'api_key'}},order:{default:['PROFILEID']}},agents:{defaults:{workspace:'~/.openclaw/workspace',model:{primary:'PROVIDER/MODEL'}}},gateway:{port:18789,bind:'loopback',auth:{mode:'token'},mode:'local'}};fs.writeFileSync(p.join(d,'openclaw.json'),JSON.stringify(config,null,2));console.log('openclaw.json written')"
```

### `auth-profiles.json`

```text
node -e "const fs=require('fs'),p=require('path'),h=require('os').homedir();const d=p.join(h,'.openclaw','agents','main','agent');fs.mkdirSync(d,{recursive:true});const auth={version:1,profiles:{'PROFILEID':{type:'api_key',provider:'PROVIDER',key:'用户提供的key'}}};fs.writeFileSync(p.join(d,'auth-profiles.json'),JSON.stringify(auth,null,2));console.log('auth-profiles.json written')"
```

## 验证写入

### bash

```bash
cat ~/.openclaw/openclaw.json | grep -E '"provider"|"primary"|"port"|"baseUrl"' && echo "---" && cat ~/.openclaw/agents/main/agent/auth-profiles.json | grep -E '"type"|"provider"' | head -3
```

### Windows

```text
node -e "const fs=require('fs'),p=require('path'),h=require('os').homedir();const c=JSON.parse(fs.readFileSync(p.join(h,'.openclaw','openclaw.json'),'utf8'));console.log('provider:',Object.keys(c.auth.profiles)[0]);console.log('model:',c.agents.defaults.model.primary);console.log('port:',c.gateway.port);if(c.models&&c.models.providers)console.log('baseUrl:',Object.values(c.models.providers)[0].baseUrl);const a=JSON.parse(fs.readFileSync(p.join(h,'.openclaw','agents','main','agent','auth-profiles.json'),'utf8'));console.log('auth type:',Object.values(a.profiles)[0].type);console.log('auth provider:',Object.values(a.profiles)[0].provider)"
```
