# OpenClaw 安装助手 — 参考索引

与 [SKILL.md](SKILL.md) 配合使用。默认优先走 OpenClaw 官方安装与更新路径；为降低上下文负担，详细内容已拆到 `references/` 目录，按需读取。

## 参考文件

| 文件 | 覆盖内容 |
|------|----------|
| [环境探测与平台规则](references/environment-detection.md) | shell 探测、Windows 安全语法、环境判断 |
| [Node.js 与 OpenClaw 安装](references/node-and-openclaw-install.md) | 官方 installer、Node.js 安装、OpenClaw 安装、升级、PATH/npm 修复、网络回退 |
| [Provider 配置模板](references/provider-config.md) | 服务商映射、Key 页面、配置写入模板、验证 |
| [启动、健康检查与排错](references/startup-and-recovery.md) | onboard、gateway、doctor、dashboard、诊断梯子 |

## 静态模板

这些文件用于快速确认配置结构，避免每次都从长命令里找 JSON：

- `assets/aihubmix-openclaw.template.json`
- `assets/builtin-openclaw.template.json`
- `assets/auth-profiles.template.json`

## 辅助脚本

- `scripts/render-config.js`：根据 provider 和 API Key 直接生成 `openclaw.json` 与 `auth-profiles.json`

## 何时读哪一份

- 需要判断 shell、平台或 Windows 受限命令时：读 `references/environment-detection.md`
- 需要判断“官方 installer 还是手工兼容路径”时：先读 `references/environment-detection.md`，再读 `references/node-and-openclaw-install.md`
- 需要选择 provider、打开 API Key 页面、写配置文件时：读 `references/provider-config.md`
- 需要 onboard、doctor、gateway、dashboard 或恢复服务时：读 `references/startup-and-recovery.md`

## 保留此文件的原因

- 兼容原先引用 `reference.md` 的内容
- 让主 Skill 仍能通过一个入口找到所有细分文档
- 保持高质量 Skill 常见的“主文件精简、参考资料按需加载”的结构
