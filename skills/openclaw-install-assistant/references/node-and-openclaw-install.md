# Node.js 与 OpenClaw 安装

在环境探测后，根据 OS、包管理器和版本管理器自动选择安装方式。默认先走官方 installer script，只有在当前终端环境不适合官方脚本或需要更细粒度控制时，才回退到手工安装。官方基线是 `Node 24` 推荐，`22.16+` 兼容。

## 官方 installer script

根据 OpenClaw 官方安装文档，installer script 是默认推荐路径：

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

它会自动探测 OS、在需要时安装 Node、安装 OpenClaw，并启动 onboarding。

官方系统要求：

- 推荐：`Node 24`
- 兼容下限：`Node 22.16+`

如果目标是“尽量与官方保持一致”，优先让 installer script 处理 Node。

如果希望安装但先跳过 onboarding：

```bash
curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
```

优先使用场景：

- 用户只想要最快、最接近官网的安装路径
- 当前环境不是严格受限的 Windows 命令白名单环境
- 不需要在安装前手动锁定 provider 配置细节

如果当前环境受限，或需要更细粒度控制，就继续使用本文件下方的手工安装路径。

## 手工安装路径何时使用

只有在这些情况下，才把手工路径当主路径：

- 当前是受限 Windows shell，不能安全运行官方 PowerShell 脚本
- 需要严格遵守固定命令白名单
- 需要在安装过程中显式控制 Node 版本、PATH 修复、provider 配置或错误恢复顺序

## 网络准备与自动回退

默认假设用户网络可用，先直接执行安装。

- 若 `npm` 或下载命令出现 `ETIMEDOUT`、`ECONNRESET`、`EAI_AGAIN`
- 先自动切换更快的镜像或下载源
- 若仍失败，再提示用户确认终端网络、代理或 VPN

对用户的说明应简洁，例如：

- `正在切换更快的下载源重试`
- `网络连接看起来不稳定，请确认终端可以联网后继续`

## 手工安装 Node.js

### 优先使用版本管理器

```bash
# nvm
nvm install 24 && nvm use 24 && nvm alias default 24

# fnm
fnm install 24 && fnm use 24 && fnm default 24
```

### macOS

```bash
# Homebrew
brew install node@24 && brew link --overwrite node@24

# 官方 pkg
curl -fsSL "https://nodejs.org/dist/latest-v24.x/$(curl -fsSL https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt | awk '/\\.pkg$/ {print $2; exit}')" -o /tmp/node-v24.pkg && sudo installer -pkg /tmp/node-v24.pkg -target / && rm /tmp/node-v24.pkg
```

### Linux

```bash
# Debian/Ubuntu
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash - && sudo apt-get install -y nodejs

# Fedora/RHEL
curl -fsSL https://rpm.nodesource.com/setup_24.x | sudo -E bash - && sudo dnf install -y nodejs

# Arch
sudo pacman -Sy --noconfirm nodejs npm
```

其他 Linux 可按架构下载 Node.js 24 二进制包到 `/usr/local`：

```bash
# x86_64
curl -fsSL "https://nodejs.org/dist/latest-v24.x/$(curl -fsSL https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt | awk '/linux-x64.tar.xz$/ {print $2; exit}')" | sudo tar -xJf - -C /usr/local --strip-components=1
# aarch64/arm64
curl -fsSL "https://nodejs.org/dist/latest-v24.x/$(curl -fsSL https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt | awk '/linux-arm64.tar.xz$/ {print $2; exit}')" | sudo tar -xJf - -C /usr/local --strip-components=1
```

### Windows

按优先级选择：

1. `winget install OpenJS.NodeJS --accept-package-agreements --accept-source-agreements`
2. `choco install nodejs -y`
3. 使用官方 Windows installer script（PowerShell 环境）或当前 Skill 的安全替代路径

官方 Windows installer script（PowerShell 环境）：

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

安装后提示用户重启终端，再验证：

```text
node --version
npm --version
```

## Node.js 安装后验证与修复

```bash
node --version && npm --version
```

PATH 修复（bash）：

```bash
NODE_FOUND=$(find /usr/local/bin /opt/homebrew/bin /usr/bin "$HOME/.local/bin" -name node -type f 2>/dev/null | head -1) && [ -n "$NODE_FOUND" ] && export PATH="$(dirname "$NODE_FOUND"):$PATH" && echo "已修复 PATH: $(dirname "$NODE_FOUND")"
```

Homebrew 冲突：

```bash
brew unlink node && brew install node@24 && brew link --overwrite node@24
```

## 手工安装 OpenClaw

### bash/zsh

```bash
SHARP_IGNORE_GLOBAL_LIBVIPS=1 npm install -g openclaw@latest && openclaw --version
```

### Windows

1. `npm install -g openclaw@latest`
2. `openclaw --version`

### pnpm（官方备选）

```bash
pnpm add -g openclaw@latest
pnpm approve-builds -g
openclaw onboard --install-daemon
```

## 官方验证链

安装完成后，优先按官方文档验证：

```bash
openclaw --version
openclaw doctor
openclaw gateway status
```

## 手工安装常见修复

### EACCES

```bash
mkdir -p "$HOME/.npm-global" && npm config set prefix "$HOME/.npm-global" && export PATH="$HOME/.npm-global/bin:$PATH" && SHARP_IGNORE_GLOBAL_LIBVIPS=1 npm install -g openclaw@latest && openclaw --version
```

仍失败时：

```bash
sudo SHARP_IGNORE_GLOBAL_LIBVIPS=1 npm install -g openclaw@latest && openclaw --version
```

### sharp / libvips

```bash
SHARP_IGNORE_GLOBAL_LIBVIPS=1 npm install -g openclaw@latest --ignore-scripts && cd "$(npm prefix -g)/lib/node_modules/openclaw" && SHARP_IGNORE_GLOBAL_LIBVIPS=1 npm rebuild sharp && openclaw --version
```

### 找不到 `openclaw`

```bash
NPM_BIN="$(npm prefix -g)/bin" && export PATH="$NPM_BIN:$PATH" && openclaw --version
```

如需长期生效，可提示用户将 `export PATH="$(npm prefix -g)/bin:$PATH"` 加入 shell 配置。

### npm 网络超时

```bash
npm config set registry https://registry.npmmirror.com && SHARP_IGNORE_GLOBAL_LIBVIPS=1 npm install -g openclaw@latest && openclaw --version
```

如果仍失败，再向用户说明网络不可达，而不是继续重复同一条命令。

### Windows PATH

执行 `npm prefix -g` 获取全局路径，并提示用户重启终端。

## 升级 OpenClaw

OpenClaw 官方文档推荐优先使用 `openclaw update`，因为它会自动识别安装方式，抓取最新版本，运行 `openclaw doctor`，并重启网关。

### 推荐路径

```bash
openclaw update
```

仅预览更新计划：

```bash
openclaw update --dry-run
```

切换通道或目标版本：

```bash
openclaw update --channel beta
openclaw update --channel dev
openclaw update --tag main
```

### 升级后检查

```bash
openclaw doctor
openclaw gateway restart
openclaw health
```

### 备用升级路径

如果 `openclaw update` 不可用或失败，可退回到包管理器安装：

```bash
npm install -g openclaw@latest && openclaw doctor && openclaw gateway restart
```

如果项目是通过 `pnpm` 全局安装：

```bash
pnpm add -g openclaw@latest && openclaw doctor && openclaw gateway restart
```

### 回退到指定版本

```bash
npm i -g openclaw@<version>
openclaw doctor
openclaw gateway restart
```

### 升级失败时

- 先执行 `openclaw update --dry-run` 查看实际计划
- 若失败与网络有关，切换镜像或下载源后再试
- 若失败与配置迁移有关，先执行 `openclaw doctor`
- 若失败与网关重启有关，改到 `references/startup-and-recovery.md` 继续排查
