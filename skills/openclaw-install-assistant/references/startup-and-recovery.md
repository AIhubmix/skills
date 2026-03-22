# 启动、健康检查与排错

在配置写入后，负责启动 OpenClaw、检查健康状态并处理常见错误。

## 诊断梯子

遇到启动失败、网关不可用或状态不明时，优先按这个顺序检查：

1. `openclaw status`
2. `openclaw gateway status`
3. `openclaw doctor --non-interactive`
4. `openclaw onboard --install-daemon --non-interactive --accept-risk --skip-channels --skip-skills`
5. `openclaw dashboard --no-open`

如果某一步已经暴露明确错误，就直接进入对应修复，不必把整条梯子跑完。

如果问题发生在升级之后，把下面这些命令插到梯子里：

1. `openclaw update status`
2. `openclaw doctor`
3. `openclaw gateway restart`
4. `openclaw health`

## 启动命令

```bash
openclaw onboard --install-daemon --non-interactive --accept-risk --skip-channels --skip-skills
```

## 启动失败时的优先修复

### gateway.mode 未设置

```bash
openclaw config set gateway.mode "local" && openclaw onboard --install-daemon --non-interactive --accept-risk --skip-channels --skip-skills
```

### 端口占用 / 已有实例监听

```bash
openclaw gateway --force && openclaw gateway install --force
```

### macOS LaunchAgent

先检查，再按需重装：

```bash
ls -la ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null && launchctl print gui/$UID/ai.openclaw.gateway 2>/dev/null
```

如果 plist 存在但服务未运行：

```bash
openclaw gateway install --force
```

### Linux systemd

```bash
systemctl --user status openclaw-gateway 2>/dev/null
loginctl show-user $USER 2>/dev/null | grep Linger
```

若未启用 linger：

```bash
loginctl enable-linger && openclaw gateway install --force
```

### Windows

先尝试：

```text
openclaw gateway install
```

若失败，可尝试计划任务：

```text
schtasks /Create /TN "OpenClaw Gateway" /TR "node %APPDATA%\npm\node_modules\openclaw\dist\gateway.js" /SC ONLOGON /RL HIGHEST /F
```

### 通用兜底

```bash
openclaw doctor --yes
```

## 健康检查

```bash
openclaw doctor --non-interactive
openclaw gateway status
```

常见修复：

```bash
# 配置文件权限
chmod 600 ~/.openclaw/openclaw.json

# 网关未运行
openclaw gateway start

# legacy 配置迁移
openclaw doctor --repair --yes
```

## 打开带 token 的仪表盘

先获取 URL：

```bash
openclaw dashboard --no-open
```

从输出中提取完整 URL，必须带 `token` 参数。不要直接打开 `http://localhost:18789`。

打开方式：

```bash
# macOS
open "完整URL"

# Linux
xdg-open "完整URL" 2>/dev/null || echo "请在浏览器中打开上面的链接"
```

```text
# Windows
cmd /c start "" "完整URL"
```

## 错误处理决策树

- `npm install` 失败：EACCES -> 用户级 prefix -> sudo；网络 -> npmmirror；sharp -> rebuild；ENOSPC -> 提醒用户清理磁盘
- `Node 安装失败`：权限 -> sudo；brew 冲突 -> unlink/link；nvm/fnm 可用时优先切换
- `openclaw 找不到`：修 PATH；Windows 让用户重开终端
- `守护进程失败`：优先检查 `gateway.mode`、端口占用、系统服务注册，再跑 `doctor`

## 完成后的简短总结模板

向用户简洁汇报：

- 安装了什么：Node.js 版本、OpenClaw 版本
- 配置了什么：服务商名称
- 已打开控制面板：带 token 的 URL
- 可继续尝试：`openclaw channels login`、`openclaw status`、`openclaw message send "你好"`
