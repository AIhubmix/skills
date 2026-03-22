# 环境探测与平台规则

在执行任何安装动作前，先完成环境探测并确定 shell 类型。探测的目标不只是识别 OS，也要判断当前终端是否适合直接走 OpenClaw 官方 installer script。

## Windows 命令限制与安全替代

若环境对 PowerShell 有白名单，避免以下写法：

| 避免 | 改用 |
|------|------|
| `Write-Output` | `echo` |
| `Start-Process` | `cmd /c start "URL"` 或提示用户手动打开 |
| `Get-Command` | `where.exe node` 或 `node --version` |
| `Test-Path` | `node -e "console.log(require('fs').existsSync('path'))"` |
| `Select-String` | `node -e "..."` 读文件 |
| `New-Item` | `mkdir` 或 `node -e "require('fs').mkdirSync(...)"` |
| `[IO.File]::WriteAllText` | `node -e "require('fs').writeFileSync(...)"` |
| `Invoke-WebRequest` | `curl` |
| `$var = ...`、`if/else`、`try/catch`、here-string | 单条命令或 `node -e` |
| `$env:VAR = ...` | 告知用户重启终端，不依赖该语法 |

原则：Windows 上文件、JSON、路径和存在性检查优先使用 `node -e "..."`。

## 语法对照

| 用途 | bash/zsh | Windows |
|------|----------|---------|
| 串联 | `cmd1 && cmd2` | 多条独立执行，或 `cmd1 & cmd2` |
| 打开浏览器 | `open` / `xdg-open` | `cmd /c start "" "URL"` |
| 存在检查 | `test -f` | `node -e` + `fs.existsSync` |
| 用户目录 | `~` / `$HOME` | `os.homedir()` / `USERPROFILE` |

## bash/zsh 环境探测

```bash
echo "=== OpenClaw Environment ===" && echo "SHELL_TYPE=bash" && echo "OS=$(uname -s)" && echo "ARCH=$(uname -m)" && echo "SHELL=$SHELL" && echo "BREW=$(command -v brew 2>/dev/null && brew --version 2>/dev/null | head -1 || echo 'not installed')" && echo "NODE=$(node --version 2>/dev/null || echo 'not installed')" && echo "NODE_PATH=$(command -v node 2>/dev/null || echo 'none')" && echo "NVM=$(command -v nvm 2>/dev/null && nvm --version 2>/dev/null || echo 'none')" && echo "FNM=$(command -v fnm 2>/dev/null && fnm --version 2>/dev/null || echo 'none')" && echo "NPM=$(npm --version 2>/dev/null || echo 'not installed')" && echo "NPM_PREFIX=$(npm prefix -g 2>/dev/null || echo 'none')" && echo "OPENCLAW=$(openclaw --version 2>/dev/null || echo 'not installed')" && echo "EXISTING_CONFIG=$(test -f ~/.openclaw/openclaw.json && echo 'exists' || echo 'none')" && echo "DISK_FREE=$(df -h / 2>/dev/null | tail -1 | awk '{print $4}')" && if [ "$(uname -s)" = "Linux" ]; then echo "DISTRO=$(cat /etc/os-release 2>/dev/null | grep ^ID= | cut -d= -f2 | tr -d '\"' || echo 'unknown')"; echo "PKG_MGR=$(command -v apt-get 2>/dev/null && echo 'apt' || command -v dnf 2>/dev/null && echo 'dnf' || command -v yum 2>/dev/null && echo 'yum' || command -v pacman 2>/dev/null && echo 'pacman' || echo 'unknown')"; echo "WSL=$(grep -qi microsoft /proc/version 2>/dev/null && echo 'yes' || echo 'no')"; fi && if [ "$(uname -s)" = "Darwin" ]; then echo "MACOS_VER=$(sw_vers -productVersion 2>/dev/null || echo 'unknown')"; fi
```

## Windows 探测（逐条执行）

1. `echo === OpenClaw Environment === & echo SHELL_TYPE=windows & echo OS=Windows`
2. `node --version`
3. `npm --version`
4. `openclaw --version`
5. `node -e "const fs=require('fs'),os=require('os'),p=require('path');const h=os.homedir();const c=p.join(h,'.openclaw','openclaw.json');console.log('EXISTING_CONFIG='+(fs.existsSync(c)?'exists':'none'));try{require('child_process').execSync('winget --version',{stdio:'pipe'});console.log('WINGET=installed')}catch{console.log('WINGET=not installed')};try{require('child_process').execSync('choco --version',{stdio:'pipe'});console.log('CHOCO=installed')}catch{console.log('CHOCO=not installed')}"`

如果 `node --version` 失败，则跳过第 5 条，直接进入 Node.js 安装。

## 探测后的判断规则

- 已装 OpenClaw + 已有配置：询问是否覆盖
- 已装 OpenClaw + 无配置：进入配置步骤
- shell 环境正常、命令不受限：优先尝试官方 installer script
- 受限 Windows shell、需要严格白名单语法或需要精细控制配置：回退到本 Skill 的手工安装路径
- 磁盘空间不足约 1GB：提醒用户清理后继续

## 官方系统要求

根据 OpenClaw 官方安装文档：

- `Node 24` 为推荐版本
- `Node 22.16+` 为兼容下限
- 官方 installer script 会在需要时自动安装合适的 Node 版本

## 官方优先策略

优先级：

1. 若当前环境能安全执行官方 installer script，优先用它
2. 若当前环境是 PowerShell 受限白名单、不能安全执行官方脚本，改走本 Skill 的兼容命令
3. 若官方安装后还需要 provider 配置、启动恢复或 dashboard 验证，再回到本 Skill 的后续步骤
