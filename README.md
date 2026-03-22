# Skills Repository

这个仓库用于集中维护项目级 Agent Skills，目标是把可复用的安装、配置、排障、工作流类能力沉淀成结构稳定、可持续扩展的 skill 集合。

## 仓库目标

- 统一管理项目内可复用的 skills
- 把主 Skill、参考资料、模板、脚本拆分清楚
- 让单个 skill 可以独立维护，也能在多项目间迁移
- 为后续新增多个 skills 提供一致的命名和目录规范

## 仓库结构

```text
.
├── README.md
└── skills/
    ├── _template/
    └── <skill-name>/
        ├── SKILL.md
        ├── reference.md
        ├── references/
        ├── assets/
        └── scripts/
```

目录说明：

- `README.md`：仓库级说明、命名规范、维护约定
- `skills/`：所有正式 skill 的根目录
- `skills/_template/`：新增 skill 时可复制的模板目录，不作为正式 skill 使用
- `skills/<skill-name>/SKILL.md`：skill 主入口，负责描述职责、边界、触发条件和执行约束
- `skills/<skill-name>/reference.md`：参考索引页，告诉 agent 何时去读哪份细分资料
- `skills/<skill-name>/references/`：按主题拆分的参考文档
- `skills/<skill-name>/assets/`：模板、静态配置、示例 JSON、样例资源
- `skills/<skill-name>/scripts/`：辅助脚本、生成器、校验工具

## Skill 目录规范

每个 skill 都应尽量遵守下面的组织方式：

- 主入口放在 `SKILL.md`
- 长文档不要直接堆进 `SKILL.md`，应拆到 `references/`
- 可复用模板放在 `assets/`
- 需要执行的辅助逻辑放在 `scripts/`
- 若需要保留“总入口”，使用 `reference.md` 作为索引页

推荐原则：

- 主文件负责“做什么、何时做、不能做什么”
- 参考文件负责“具体命令、详细流程、异常分支”
- 模板文件负责“结构真源”
- 脚本负责“减少手工操作和生成错误”

## 多 Skill 命名约定

为避免仓库扩展后出现命名混乱，统一采用以下规则：

- skill 目录名使用 `kebab-case`
- 名称应直接表达能力，不要使用模糊缩写
- 优先使用 `领域-动作-对象` 或 `产品-动作-用途` 结构
- 名称应偏能力描述，而不是实现细节描述
- 除非确有必要，不要把版本号写进 skill 名称
- 不要使用空格、下划线、中文目录名

推荐示例：

- `openclaw-install-assistant`
- `openclaw-upgrade-assistant`
- `provider-config-writer`
- `gateway-recovery-helper`
- `node-runtime-bootstrap`

不推荐示例：

- `openclaw`
- `installSkill`
- `openclaw_install`
- `my-skill`
- `skill-v2`

如果一个 skill 同时覆盖多个独立能力，优先拆成多个 skill，而不是继续把目录名变长、把职责变重。

## 新增 Skill 的建议流程

1. 先确定 skill 的唯一职责和边界
2. 按命名约定创建 `skills/<skill-name>/`
3. 先写 `SKILL.md`，明确触发条件、执行顺序、限制条件
4. 再把长内容拆到 `references/`
5. 把模板和示例补到 `assets/`
6. 如需自动生成或写配置，再补 `scripts/`
7. 最后把该 skill 追加到本 README 的清单中

## 当前 Skills

- `skills/openclaw-install-assistant/`：OpenClaw 安装、配置、升级、健康检查与恢复

## 模板目录

- `skills/_template/` 是仓库内部保留目录，用来创建新 skill
- 新建 skill 时，复制它并重命名为符合规范的 `kebab-case` 目录名
- 模板目录本身不应被当作可发布的正式 skill

## 维护建议

- 新增 skill 时先考虑是否能复用已有模板或脚本
- 避免不同 skill 内部复制同一份长文档
- 若多个 skill 会共享资源，后续可以再引入公共目录，但在当前阶段优先保持每个 skill 自包含
- 修改结构时，优先保证 `SKILL.md` 到 `reference.md` 再到 `references/` 的跳转关系稳定
