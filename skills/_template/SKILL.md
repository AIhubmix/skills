---
name: your-skill-name
description: Briefly describe what this skill does, when it should be used, and what problems it solves.
compatibility:
  os: [macOS, Linux, Windows]
metadata:
  owner: project
  style: structured
---

# Skill Title

一句话说明这个 skill 的职责。

## When To Use

在这些场景使用本 skill：

- 场景 1
- 场景 2
- 场景 3

## Do Not Use

以下情况不要使用本 skill：

- 超出职责边界的问题
- 与当前 skill 无关的通用任务

## Execution Contract

执行时应遵守：

1. 先说明当前要做什么
2. 优先使用稳定、可验证的流程
3. 出错时先分类，再选择修复路径
4. 不泄露敏感信息

## Workflow

建议按以下顺序执行：

1. 前置检查
2. 核心操作
3. 结果验证
4. 失败恢复

## Reference Files

按需读取，不要一次性加载全部内容：

| 文件 | 用途 |
|------|------|
| `references/topic-a.md` | 主题 A 的详细说明 |
| `references/topic-b.md` | 主题 B 的详细说明 |

静态资源放在 `assets/`：

- `assets/example.json`

辅助脚本放在 `scripts/`：

- `scripts/example.js`

## Safety Rules

- 不执行与当前职责无关的操作
- 不修改未授权的配置
- 不展示或回显敏感数据

## Resource Loading

- 需要看详细流程时：打开 `reference.md`
- 需要看具体主题时：打开 `references/` 下对应文件
- 需要生成配置时：查看 `assets/` 与 `scripts/`
