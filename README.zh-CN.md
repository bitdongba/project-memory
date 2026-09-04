# Project Memory

[English](README.md)

Project Memory 是一个纯 Skill 插件，用 Markdown 保存可持久、可审阅的项目上下文。它让 Codex 和 Claude Code 共享同一套 `.planning/` 项目记忆，用来管理需求、决定、术语、交接状态、经验和项目历史，同时要求容易变化的运行事实回到一手证据中核验。

`0.2.0` 在 schema 1 之上新增了可选的 ruleset 1 健康契约，把 canonical
写入路由和“只防新增恶化”的检查变成可机读约束，同时不会静默修改旧项目。
`0.1.1` 新增了带门禁的新项目初始化，以及“零写入审计、逐项批准”的存量迁移流程。

## 它能做什么

- 创建或迁移项目记忆，不整批覆盖已有文档。
- 区分已验证事实、用户决定、假设和待确认问题。
- 将稳定上下文、当前交接快照和时间线历史分开保存。
- 可按项目选择启用 ruleset：通过带角色的文档索引路由待写内容，并以
  `ERROR`、`REVIEW`、`WARNING`、`NOTICE` 四级报告健康问题。
- 可将启发式存量债务与经过明确审阅的 baseline 比较，但不会自动写入、刷新或放宽 baseline。
- 精确保留否定需求、顺序保证、数字默认值和验收标准。
- 只有当歧义实质影响范围、风险、成本、流程、架构或验收时才集中澄清。
- 可复用经验必须逐项经过用户审阅后才能进入长期经验库。
- 支持“受治理的进化”：以当前项目内、有证据、可回滚的试用改进流程，试用与最终采用都由用户决定。
- Codex 通过 `AGENTS.md`、Claude Code 通过 `CLAUDE.md` 指向同一套 `.planning/`。

Project Memory 将 `.planning/` 视为“人的意图”的长期权威记录，但不会让文档替代代码、配置、测试、命令输出、数据、制度或其他一手证据。

## 安全与隐私

Project Memory 没有后台服务、遥测、MCP Server、生命周期 Hook 或自动更新器。只有宿主调用 Skill 时它才会运行；包内的验证器和路由器也只会在被明确调用时运行，而且均为只读。

Skill 可能在宿主沙箱与审批规则允许的范围内读取项目文件，并写入 `.planning/`、`AGENTS.md` 或 `CLAUDE.md`。它不得静默扫描无关项目、修改自身源码、发布变更或更新已安装副本。

不要把秘密写入项目记忆。路径优先使用仓库相对路径，敏感内容使用脱敏引用。提交 `.planning/` 前请人工检查：即使不含凭据，需求、协作偏好、命令和本机路径仍可能具有敏感性。安全问题与数据处理方式见 [SECURITY.md](SECURITY.md)。

## 仓库结构

```text
.
├── .codex-plugin/plugin.json
├── .claude-plugin/plugin.json
├── docs/                       # 面向人的详细工作流指南
└── skills/
    └── project-memory/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── references/              # 拆分后的模板、迁移、入口与进化规则
        └── scripts/                 # 确定性验证辅助脚本
```

仓库根目录是插件包，`skills/project-memory/` 同时也是可独立安装的 Skill。面向人的文档保留在仓库根或 `docs/`，不复制到独立 Skill 中。

## 安装

同一个宿主请选择“插件安装”或“独立 Skill 安装”之一；两种方式同时安装可能导致同一 Skill 出现两次。

### Codex 插件

推荐分发方式是以仓库根目录作为原生插件包。本地测试时，让 Codex 内置的 plugin creator 为现有 checkout 创建个人 marketplace 条目。这个请求只负责 marketplace 登记，不应重新脚手架或覆盖插件：

```text
Use $plugin-creator to register the existing plugin checkout at /absolute/path/to/project-memory in my personal marketplace for local testing. Preserve the checkout and do not scaffold or overwrite the plugin.
```

刷新 Codex，在对应 marketplace 中安装 **Project Memory**，然后新建任务。当公开仓库或组织 marketplace 已包含本插件条目时，可以添加该 marketplace，再从 `/plugins` 浏览器安装：

```bash
codex plugin marketplace add <owner>/<repository>
```

GitHub 简写只适用于包含有效 marketplace catalog 的仓库；单独存在插件 manifest 并不等于 catalog。Marketplace 与安装机制以 [Codex 官方插件文档](https://developers.openai.com/plugins/)为准。

### Claude Code 插件

测试本地插件目录：

```bash
claude --plugin-dir /absolute/path/to/project-memory
```

需要持久托管安装时，通过 Claude Code marketplace 添加本仓库并安装其中的 `project-memory` 条目；安装后新建 Claude Code 会话。Marketplace 配置以 [Claude Code 官方插件文档](https://code.claude.com/docs/en/plugins)为准。

### 独立 Skill

在仓库根执行，只安装 `skills/project-memory/`。

Codex 用户级安装：

```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/project-memory "$HOME/.agents/skills/"
```

`$HOME/.agents/skills/project-memory/` 是当前 Codex 用户级目录。Codex 也会从工作目录到仓库根逐级发现 `.agents/skills/` 下的项目级 Skill。

Claude Code 用户级安装：

```bash
mkdir -p "$HOME/.claude/skills"
cp -R skills/project-memory "$HOME/.claude/skills/"
```

Claude Code 项目级安装可将该目录复制到项目内的 `.claude/skills/project-memory/`。更新前先检查已有副本，避免覆盖本地自定义修改。

本项目没有后台或自动更新。需要更新时，请主动拉取或下载 Release，阅读变更，再有意识地更新插件或独立 Skill 副本。

## 使用方法

直接用自然语言描述目标即可。Codex 也可以使用 `$project-memory` 显式调用；Claude Code 的显式调用方式取决于它是作为插件还是独立 Skill 安装。

完整的人类操作流程——包括真正的新项目初始化，以及“零写入审计、逐项批准后迁移”的存量项目流程——见 [新建与迁移指南](docs/workflows.zh-CN.md)。

允许写入前先选择路径：

- 真正的新长期项目：只读预检后，在明确初始化请求范围内建立最小结构；
- 已有需求、决定、交接、经验、同类项目记忆宿主规则或旧版/外来记忆规范的项目：零写入审计、编号方案、逐项批准，再执行已批准迁移；
- 不需要长期上下文的一次性任务：不要初始化 Project Memory。

初始化真正的新长期项目：

```text
使用 Project Memory 在当前目录建立长期项目上下文。先只读预检；如果已有资料承担项目记忆角色，请切换为迁移审计并在写入前停止，否则只创建有真实内容的最小结构。
```

迁移前只读审计已有项目：

```text
使用 Project Memory 审计当前项目文档，暂时不要写文件。列出 canonical 文档、冲突、过期表述、缺失入口规则，以及最小安全迁移方案。
```

执行已批准的迁移：

```text
严格执行 Project Memory 方案 PM-MIG-example revision 1 中已批准的 MIG-01 和 MIG-03；不要执行其他迁移项或修改其他文件。先复查批准所依据的基线，再报告实际 diff 和验证证据。
```

### 可选的 ruleset 1 健康契约

schema 与 ruleset 是两个独立版本。没有 ruleset 的 schema 1 项目仍然有效，安装或更新 Skill 不会自动升级它。启用 ruleset 1 属于存量迁移：Context 声明、带类型的角色索引、冲突维护规则，以及所有适用 `AGENTS.md` / `CLAUDE.md` 的 marker，必须作为一个原子组审阅和批准。

项目已经选择启用后，可显式运行只读健康检查：

```bash
python3 skills/project-memory/scripts/validate_project_memory.py \
  /path/to/project --health
python3 skills/project-memory/scripts/validate_project_memory.py \
  /path/to/project --health --format json
```

只有在精确 candidate 已被单独审阅、批准后，才能使用 baseline：

```bash
python3 skills/project-memory/scripts/validate_project_memory.py \
  /path/to/project --health \
  --baseline .planning/<approved-baseline>.json \
  --baseline-sha256 <approved-sha256> --format json
```

只有当调用方在被检查变更之外独立固定或保护预期摘要时，该摘要才是可信锚点。在同一项未受保护的变更中同时更新 baseline 与摘要，不构成独立门禁。

在已经获得写入授权的前提下，可先用只读路由器把明确的内容类型解析到项目角色索引中的 canonical 目标：

```bash
python3 skills/project-memory/scripts/route_project_memory.py \
  /path/to/project --kind historical-event --format json
```

路由成功只说明目标唯一，并不授权写文件；路由缺失或歧义必须交给人审阅。默认 enforcement level 是 `advisory`；pre-commit Hook、CI workflow 和 required check 都是独立变更，需要各自的 `MIG-*` 项与批准。详见 [健康检查与 ruleset 1](skills/project-memory/references/health.md)。

沉淀可复用经验：

```text
沉淀一下
```

这句话只会启动审阅，不代表一次性批准全部候选。每条经验都可以确认、修改或跳过。

## 受治理的进化

Project Memory 不会靠定时器自行唤醒。“定期审阅”只会在 Skill 再次被调用，并且用户主动要求或约定的审阅条件已满足时发生。

新建或迁移长期项目时，它会询问一次评审模式：按里程碑、每月、手动或关闭。用户不回答时保持 `manual`。主动评审只会发生在自然任务节点，需要足够的有效证据，并遵守已配置的周期和冷却时间。

V1 只能在当前项目的记忆协议中实施可回滚试用，不能修改已安装 Skill、其他项目、本 GitHub 仓库、marketplace 或已发布 Release。

进化审阅应当：

1. 展示重复摩擦或遗漏场景的具体证据。
2. 区分当前项目修正与通用 Skill 改进想法，并明确后者不在本流程的执行范围内。
3. 给出选项、推荐、兼容性影响、迁移需求和验证方案。
4. 让用户逐项确认、修改、延后或拒绝重要变更。
5. 只实施用户明确批准的当前项目试用，并记录回滚路径。
6. 验证结果、收集结果证据，再分别询问采用、调整、停止或回滚。

同意讨论改进，不等于同意编辑、发布、push、创建 Release 或更新已安装副本。跨项目审阅和上游推广不属于 V1 流程；必须另开维护任务，并单独批准输入范围、最小化和脱敏方案。

示例：

```text
审阅当前项目的 Project Memory 协议是否需要受治理的进化。展示证据和备选方案；未经我批准一个边界明确、可回滚的试用前，不要修改项目。
```

## 更新旧项目

更新已安装的插件或 Skill 不会自动改写使用过旧版本的项目。应在每个项目中先运行零写入审计，再对编号 `MIG-*` 迁移项逐项批准、修改、拒绝或延后。Project Memory 应沿用既有的 `CONTEXT.md`、`STATE.md`、`docs/adr/` 或经验库等约定，不创建互相竞争的新副本。启用 ruleset 1 时，稳定意图与协议设置固定留在 `.planning/context.md`；单独的旧 `CONTEXT.md` 可继续作为被索引的专题或链接来源。

ruleset 1 也遵循同样边界：发现新版可用只是一条 `NOTICE`，不是启用许可。不得让 Context 与宿主入口处于混合 ruleset 状态，也不得借普通文档修复之机创建或刷新健康 baseline。

如果希望在大范围迁移前建立保护性 Git commit 或备份，请由人提前创建，或另行明确授权。批准 `MIG-*` 项本身不授权 commit，也不授权新建备份路径。

## 开发

简短的仓库说明放在根目录，详细的人类指南放在 `docs/`；只有 Agent 执行时需要的文件才放入 `skills/project-memory/`。

在仓库根运行测试：

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

存在项目验证器时，可对 fixture 或项目根运行：

```bash
python3 skills/project-memory/scripts/validate_project_memory.py /path/to/project
```

ruleset 健康检查与路由检查也都是只读：

```bash
python3 skills/project-memory/scripts/validate_project_memory.py /path/to/project --health --format json
python3 skills/project-memory/scripts/route_project_memory.py /path/to/project --kind stable-intent --format json
```

构建确定性的独立 Skill、Codex 插件和 Claude Code 插件压缩包：

```bash
python3 scripts/build_release.py
```

修改行为或模板前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)
