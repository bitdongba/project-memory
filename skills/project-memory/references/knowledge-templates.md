# Project knowledge templates

Use one canonical home per subject. Create a record only after a real topic,
term, decision, or confirmed experience exists. Before allocating a sequential
ID, re-read its index and check uniqueness; concurrent projects may adopt
date-plus-slug IDs instead.

## Contents

- [Topic record](#topic-record)
- [Glossary](#planningglossarymd)
- [Decision index](#planningdecisionsmd)
- [ADR-style decision](#adr-style-decision)
- [Confirmed experiences](#planningexperiencesmd)
- [Experience review draft](#experience-review-draft)
- [Existing lessons file](#existing-lessons-file)

## Topic record

```md
# <专项标题>

- 状态：待办 / 进行中 / 阻塞 / 已完成 / 长期维护
- 最后更新：<YYYY-MM-DD>

## 背景与目标

-

## 范围

### 包含

-

### 不包含

-

## 需求与验收标准

| ID | 类型 | 精确要求 | 来源/确认 | 验证方式 | 状态 |
|---|---|---|---|---|---|
| R-001 | 功能 / 约束 / 否定需求 / 顺序 / 数值默认 |  |  |  | 待确认 |

## 已验证事实

| 事实 | 一手来源 | 验证日期 | 备注 |
|---|---|---|---|
|  |  | <YYYY-MM-DD> |  |

## 决定

### <YYYY-MM-DD> <标题>

- 类型：用户决定
- 确认方式：<会话、会议或批准记录>
- 决定：
- 理由：
- 影响：
- 关联需求或验证：

## 计划与验证

1.

## 风险、假设与待确认

-

## 专项历史

- <YYYY-MM-DD>：
```

Remove empty sections. Do not copy changeable code or configuration facts into
the topic when a stable link to primary evidence is enough.

## `.planning/glossary.md`

Create after the first project-specific term is resolved.

```md
# <项目名> Glossary

> 只记录项目专有术语和约定含义，不保存实现细节或通用概念。

- 最后更新：<YYYY-MM-DD>

## <规范名称>

- 定义：<一到两句话>
- 避免使用：<易混淆同义词；没有则删除>
- 确认依据：<用户确认或权威文档>
```

## `.planning/decisions.md`

Use for ordinary material decisions and as the real index of individual ADRs.

```md
# <项目名> Decisions

## 重大决定索引

| ID | 决定 | 状态 | 日期 | 关联主题 |
|---|---|---|---|---|
| [0001](decisions/0001-example.md) | 示例 | accepted | <YYYY-MM-DD> | `.planning/<topic>.md` |

## 普通决定

### <YYYY-MM-DD> <标题>

- 类型：用户决定
- 确认方式：
- 决定：
- 理由：
- 影响：
- 关联需求或验证：
```

## ADR-style decision

Create an individual record only when the decision is costly to reverse,
surprising without rationale, and based on a genuine trade-off.

```md
# <ID> <决定标题>

- 状态：proposed / accepted / deprecated / superseded
- 日期：<YYYY-MM-DD>
- 确认方式：<用户、会议或批准记录>
- 关联文档：<需求、专项、验证或被替代决定>

## 背景

<为什么现在需要决定。>

## 决定

<精确写明选择，包括否定要求、边界和默认值。>

## 理由与权衡

-

## 考虑过的方案

- <方案及未采用原因>

## 后果

- 正面：
- 代价或风险：
- 后续验证：
```

## `.planning/experiences.md`

Create only after the first candidate is individually reviewed and confirmed.
Keep proposed drafts out of this canonical library.

```md
# <项目名> Confirmed Experiences

> 只保存经人工确认且范围明确的可复用经验；经验不能替代当前一手事实。

- 最后更新：<YYYY-MM-DD>

## 索引

| ID | 类型 | 标题 | 状态 | 适用范围 | 最近验证 |
|---|---|---|---|---|---|
| EXP-001 | insight / habit / lesson / solution |  | confirmed / validated / deprecated / superseded |  | 未验证 |

## EXP-001 <标题>

- 类型：insight / habit / lesson / solution
- 状态：confirmed / validated / deprecated / superseded
- 确认日期与方式：<YYYY-MM-DD；用户确认、会议或批准记录>
- 精确结论或做法：
- 适用范围：
- 不适用或停止条件：<没有则删除>
- 来源与证据：
- 验证情况：<尚未实证 / 一次成功 / 多次成功及引用>
- 关联文档：
- 替代关系：<没有则删除>
```

## Experience review draft

Keep the state checkpoint independent from the experience decision. Present
each candidate separately in chat before canonical storage.

```md
## 建议状态更新

- 刚刚完成：
- 正在处理：
- 精确下一步：
- 阻塞或待确认：
- 恢复引用：

## 建议沉淀条目

### 候选 1：<标题>

- 类型：insight / habit / lesson / solution
- 建议状态：confirmed / validated
- 精确结论或做法：
- 适用范围：
- 不适用或停止条件：
- 来源与证据：
- 验证情况：

请逐项回复：确认 / 修改为…… / 跳过。
```

`validated` requires named outcome evidence. The agent following a rule it
wrote is not independent validation.

## Existing lessons file

When the project already has a canonical lessons file, adapt this entry instead
of creating a duplicate experience library:

```md
## <YYYY-MM-DD> <问题标题>

- 发生了什么：
- 根因：
- 影响：
- 以后如何避免：
- 是否更新流程或检查清单：
- 证据与关联文档：
```
