# 记忆系统协议

Orchestrator 在 pipeline 运行过程中沉淀和复用经验，分两层：

| 类型 | 路径 | 范围 | 谁写 | 谁读 |
|---|---|---|---|---|
| **项目经验** | `.ai-dev/memory/project.md` | 仅当前项目 | orchestrator 在 Human Gate APPROVE 后总结 | orchestrator 在调度任意 agent 时注入 prompt |
| **Agent 经验** | `~/.claude/memory/agents/{agent-name}.md` | 跨项目，仅该 agent | orchestrator 在 Human Gate APPROVE 后总结 | orchestrator 在调度该 agent 时注入 prompt |

**subagent 不直接读 memory 文件**。orchestrator 拼进 prompt 才生效，保证 agent 不知道 memory 在哪、也不能直接改。

## 1. 存储格式

### 1.1 项目经验 `.ai-dev/memory/project.md`

```markdown
# 项目经验：{project_name}

> 由 orchestrator 在每个阶段 APPROVE 后自动追加。该文件随项目走，会被 commit。

## 经验条目

- [2026-06-09 stage:requirement-analysis DEC-001] 本项目 product_id = hipro，版本 v3.2，所有 baseline API 检索基于此
- [2026-06-09 stage:solution-design DEC-003] 团队决定不引入新的数据库表，复用现有 user_profile.address 字段
- ...
```

### 1.2 Agent 经验 `~/.claude/memory/agents/{agent-name}.md`

```markdown
# {agent-name} 全局经验

> 由 orchestrator 在每个阶段 APPROVE 后总结。**仅记录通用方法论改进，不要写项目特定细节。**

## 经验条目

- [2026-06-09] WebFetch 对 SSO 内网系统总返回登录页，应直接跳到 Playwright + 持久化 profile
- [2026-06-12] product_id 字段在 ticket 页 URL 参数里常见 (bizId=...)，可作为兜底提取来源
- ...
```

## 2. 条目格式

固定一行格式，便于扫读和增量追加：

```
- [{YYYY-MM-DD} stage:{stage-name} {DEC-id?}] {one-line lesson}
```

- 项目经验必须含 `stage` 和 `DEC-id`（关联到 decision-log）
- Agent 经验 `stage` 和 `DEC-id` 可省略，因为是跨项目的
- lesson 单行，≤ 120 字符；触及多点拆成多条

## 3. 写入触发

### 3.1 触发时机

仅在 Human Gate `gate_decision = APPROVE` 时触发，**且仅对当前阶段的 agent**。

REVISE / REJECT / SKIP 不触发（产物没被认可，不沉淀错误经验）。

### 3.2 总结流程

1. orchestrator 读：
   - 本阶段 artifact（如 `artifacts/01_requirement.json`）
   - decision-log 里本阶段的决策（用户的修改意见、问题答案）
   - issue-log 里本阶段的 warning（如有）
2. orchestrator 自动生成两类候选条目：
   - **项目经验候选**：本项目特定的事实（产品 ID、版本、决策、踩坑） — 0-3 条
   - **Agent 通用经验候选**：可复用到其他项目的方法论改进 — 0-2 条
3. **兜底规则（禁止空跳过）**：如果两类候选总计 == 0，必须生成至少 1 条"本阶段事实记录"作为项目经验候选。格式示例：
   ```
   - [{date} stage:{stage} DEC-{id}] 本阶段确认 product_id={xxx} version={yyy}，{关键决策或结论一句话}
   ```
   确保**每个 APPROVE 至少有一条记忆沉淀**。不存在"本阶段没什么可记的"。
4. orchestrator 用 `AskUserQuestion` 让用户审核每一条：保留 / 修改 / 丢弃
5. 保留的条目追加到对应文件末尾

### 3.3 AskUserQuestion 调用模板

```
AskUserQuestion(
  questions: [
    {
      question: "项目经验候选 1/N：是否保存？\n\n候选条目：[2026-06-09 stage:req DEC-002] 本项目 product_id=hipro v3.2",
      header: "Mem-Proj-1",
      multiSelect: false,
      options: [
        {label: "保留 (推荐)", description: "追加到 .ai-dev/memory/project.md"},
        {label: "修改后保留", description: "用户提供新文本，再追加"},
        {label: "丢弃", description: "不沉淀"}
      ]
    },
    // ... 最多 4 条/批
  ]
)
```

如果同时有项目+Agent 经验候选，分批问，每批 ≤ 4 条。

## 4. 读取注入

### 4.1 注入时机

orchestrator **每次调度 agent 前**，从两个文件读取经验，拼进 agent 调度 prompt。

### 4.2 prompt 拼接位置

在 agent 调度 prompt 的 `## 输入` 段之后、`## 输出要求` 之前，插入：

```
## 历史经验（参考，非强制）

### 本项目经验
（如果 .ai-dev/memory/project.md 不存在或为空，本段省略整段不要出现）
- {条目1}
- {条目2}

### {agent-name} 全局经验
（如果 ~/.claude/memory/agents/{agent-name}.md 不存在或为空，本段省略整段不要出现）
- {条目1}
- {条目2}
```

### 4.3 注入条目数限制

- 项目经验：本项目全部条目都注入（项目本身有边界，预期 < 50 条）
- Agent 经验：取**最近 20 条**（按时间倒序），超出的不注入

### 4.4 Agent 端语义

agent.md 中明确说明：`## 历史经验` 段是参考信息，**不要把它当作 reference 文件路径去读，也不要当作硬约束。** 仅在与当前任务相关时影响判断。

## 5. 经验归并

### 5.1 Agent 经验归并

`~/.claude/memory/agents/{agent}.md` 条目数 > 50 时，orchestrator 在下次 Human Gate APPROVE 时触发归并：

1. 读取全部条目
2. 用 AskUserQuestion 询问用户："{agent-name} 全局经验已超 50 条，是否归并？"
3. 用户同意 → orchestrator 输出归并后的精简版（保留前 20 条最有价值条目 + 合并相似条目），写回文件
4. 用户拒绝 → 保留现状，但在 prompt 注入时只用最近 20 条

### 5.2 项目经验归并

项目经验**不归并**。项目本身是有边界的，最多 50-100 条不会有性能问题。

## 6. 初始化

### 6.1 项目级

第一次 Human Gate APPROVE 时，如果 `.ai-dev/memory/` 不存在：
1. 创建目录
2. 创建 `project.md`，写入 header：
   ```markdown
   # 项目经验：{project_name}

   > 由 orchestrator 在每个阶段 APPROVE 后自动追加。

   ## 经验条目
   ```

### 6.2 全局级

第一次需要写入某 agent 全局经验时，如果 `~/.claude/memory/agents/` 不存在：
1. 创建目录
2. 创建 `{agent-name}.md`，写入 header（与项目级类似但描述不同）

## 7. 不要做

- ❌ 不要让 subagent 直接读写 memory 文件（违反 orchestrator 单一职责）
- ❌ 不要把项目特定细节（product_id、用户名、API 路径）写进 Agent 全局经验
- ❌ 不要把 memory 内容当作硬约束注入（用 `（参考，非强制）` 标注）
- ❌ 不要在 REVISE/REJECT 时也总结经验 — 那是失败路径
- ❌ 不要自动覆盖或删除现有条目（只追加；归并是用户显式触发）
