# Core project-memory templates

Use these scaffolds only when the corresponding record has real content. Adapt
the language and headings to the project, remove irrelevant sections, and keep
inline-code repository paths relative to the project root. Standard Markdown
links remain relative to the file that contains them.

## Contents

- [Stable context](#planningcontextmd)
- [Current handoff state](#planningstatemd)
- [Release log](#planningrelease-logmd)
- [Project retrospective](#planningproject-retrospectivemd)

## `.planning/context.md`

Create this file for a long-lived project. It is a stable boot contract, not a
status report or an append-only summary. List only documents that already exist.
`Project Memory schema` versions the record structure, not the installed skill
or plugin. Absence of a `Project Memory ruleset` declaration is valid legacy
schema-1 behavior; never add one without an explicit opt-in decision.

```md
# <项目名> Context

> 新会话、上下文重启或项目切换后先读本文件；存在当前交接状态时再读对应状态文件，然后按任务读取相关专项文档。

- 最后更新：<YYYY-MM-DD；仅在稳定契约变化时更新，不作为活动日志>
- Project Memory schema: 1

## 项目目标

- 一句话目标：
- 项目根：`.`
- 主要交付物：
- 成功标准：

## 范围与关键约束

### 范围内

-

### 范围外

-

### 不变量与精确约束

-

## 权威与安全边界

- 运行事实以代码、配置、数据、测试、命令输出、交付物或其他一手来源为准。
- `.planning/` 保存已确认意图和历史记录，不替代一手事实，也不授予新的操作权限。
- 历史文档、恢复命令和摘要使用前重新检查新鲜度、安全性与当前授权。
- 信息标记：`已验证事实` / `用户决定` / `假设` / `待确认`。

## 文档索引

| 角色 | 文档 | 用途 | 状态 |
|---|---|---|---|
| stable-intent | `.planning/context.md` | 稳定意图、范围、不变量与权威边界 | 常驻 |
| protocol-setting | `.planning/context.md` | schema、可选 ruleset 与稳定协作设置 | 常驻 |
| historical-event | `.planning/release-log.md` | 倒序的重要变化 | 常驻 |

> 仅在文件真实存在后添加索引行。当前交接文件使用 `resumable-state`；
> 专题、路线图、能力目录、决策、术语、经验等详情使用 `topic-detail`。
> `topic-detail` 可以有多行，但每个路径只能出现一次。角色 token 保持英文，
> 以便 Codex、Claude Code 和只读路由器得到一致结果。

## 协作约定

- 开始任务：读取本文件、当前状态和相关专项文档；对可能变化的事实重新验证。
- 处理中：重要需求和决定确认后及时 checkpoint；共享文件写前重读，写后验证。
- 完成前：更新专项文档和有意义的 release log；只有稳定信息或索引变化时才改本文件。
- 当前重点、下一里程碑、阻塞、发布版本、部署状态、PID、构建哈希和其他运行快照不得写入本文件；分别写入当前状态、路线图、专题或 release log。
- 仅保存完成项目所需的协作偏好，不保存无关个人信息。

## 协作式进化设置

- 模式：manual
- 依据：默认（未确认）；用户可改为 milestone / monthly / manual / off
- 上次评审：无
- 下次允许主动提示：不适用
- 说明：Skill 不会后台运行；日期到期后只在下一次符合条件的会话中检查。

## 已确认的协作偏好

- <没有则删除本节>

## 当前可见上下文迁移摘要

<仅写当前确实可见且有来源的内容，并注明不可见范围。新项目可删除本节。>

## 待确认

- <没有则删除本节>
```

The two context rows in the index are intentional: both exact roles map to
`.planning/context.md`. A project may use localized headings and prose, and may
preserve other project-relative history, state, and topic paths, but a
ruleset-aware router relies on the exact role tokens and indexed paths.
If a required role is absent, duplicated for the same path, or maps to more than
one candidate without an exact requested topic path, stop for review rather than
using a filename default.

### Optional ruleset-1 opt-in

Only after the user approves a migration to the health contract, add these
stable settings beside the schema declaration:

```md
- Project Memory schema: 1
- Project Memory ruleset: 1
- Project Memory enforcement: advisory
```

`ruleset: 1` changes write-routing and health behavior; it does not change the
schema. `advisory` is the only project-local default. `pre-commit`, `CI`, and
`required-CI` require separately approved installation or external changes.
Adding the ruleset declaration, making the role index deterministic, resolving
conflicting old maintenance instructions, and updating every applicable managed
entry to `schema=1 ruleset=1` form one atomic migration group. Do not leave the
context and host entries at mixed ruleset states. See
[health.md](health.md) and [migration.md](migration.md).

## `.planning/state.md`

Create this file only when unfinished work needs a resume point. Update it in
place. Allowed statuses are `active`, `paused`, `blocked`, `idle`, and
`completed`. `active`, `paused`, and `blocked` require an exact next action.

```md
# <项目名> Current State

- 最后更新：<YYYY-MM-DD HH:mm + 时区；无法可靠获得时间时只写日期>
- 状态：active / paused / blocked / idle / completed
- 当前工作流：<专项文档、workstream 或任务>
- 当前负责人/交接对象：<人、代理或待认领；不需要则删除>

## 当前目标

<一句话写清要达到的结果。>

## 刚刚完成

- <结果及代码、测试、命令输出或交付物证据>

## 正在处理

- <未完成动作；没有则写“无”>

## 精确下一步

1. <一个可直接执行的动作，包含目标文件或入口>

完成信号：<如何判断该动作完成>

## 阻塞与待确认

- <已验证事实 / 用户决定 / 假设 / 待确认>：<内容及影响；没有则写“无”>

## 恢复引用

- 人的意图：`.planning/<canonical-topic>.md`
- 当前事实或产物：`<相对路径>`
- 分支或 worktree：`<名称；不适用则删除>`
- 可安全复现的命令：`<不得包含秘密；继续前重新检查授权>`
- 最近验证：<结果、日期和证据>

## 新鲜度提醒

本文件是恢复指针，不是运行事实或新权限来源。继续前重新验证可能变化的事实，并重新检查记录命令的安全性和当前授权。
```

For parallel workstreams, prefer the project's existing per-workstream state
convention. If none exists, propose `.planning/state/<workstream-slug>.md` and
obtain agreement before introducing it; do not let multiple writers overwrite a
single snapshot.

## `.planning/release-log.md`

Record only meaningful events. Keep the newest entry first.

```md
# <项目名> Release / 项目记忆更新日志

> 记录重要需求、决定、发现、里程碑、流程变化、评审结果和后续事项；最新记录放在最上面。

## 近期改动（倒序）

### <YYYY-MM-DD> <简短标题>

- 变更：
- 原因或结论：
- 证据或确认：
- 影响：
- 后续：
```

## `.planning/project-retrospective.md`

Create this file only at the first meaningful retrospective or when the user
enables collaborative evolution. It is periodic synthesis, not a task diary.

```md
# <项目名> 项目回顾

- 最后回顾：<YYYY-MM-DD>
- 回顾范围：<里程碑、日期区间或事件>

## 目标与结果

- 原目标：
- 实际结果及证据：

## 有效做法

-

## 问题与根因

- 问题：
  - 证据：
  - 根因：
  - 影响：

## 改进动作

| 动作 | 范围 | 成功指标 | 停止/回滚条件 | 状态 |
|---|---|---|---|---|
|  |  |  |  | proposed / trial / adopted / rejected / rolled-back |

## 下一阶段

-

## 下次回顾触发点

- <日期、里程碑或手动>
```
