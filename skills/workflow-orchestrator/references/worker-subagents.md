# Worker SubAgents

worker 内部 subAgent 是可选优化，用来减少 worker 自身上下文污染。它不是主 session 和 worker 隔离的前提。

## 默认策略

- 普通阶段先不启用 subAgent，保持 worker 简洁。
- 当阶段包含大量 ticket、网页、文档、代码检索、MCP 查询、候选 API 查找或风险审查时，主流程可以内部启用 worker subAgent。
- 如果用户明确要求“不使用 subAgent / 只用单 worker”，主流程不要启用 worker subAgent。
- 是否启用必须记录在 `workflow-state.json.worker_subagents_enabled` 和 `worker-run-metrics.json.worker_subagents_enabled` 中，便于审计。

## 默认 SubAgent

- `workflow-requirement-researcher`：用于需求阶段的大量 ticket、文档、网页或代码检索。
- `workflow-design-researcher`：用于方案阶段的 API、平台上下文、依赖和候选实现检索。
- `workflow-risk-reviewer`：用于方案阶段的风险、缺失决策和验证准备度审查。

## 使用边界

- subAgent 只处理高噪声、可独立的局部任务，例如资料检索、候选 API 查找、风险审查。
- subAgent 不写阶段产物，不更新 workflow state，不直接问用户。
- worker 必须汇总 subAgent 结果，再写正式文档、handoff、validation、pending-questions 或 worker-result。
- 需要用户确认时，仍由 worker 写 `pending-questions.json`，再由主 session 问用户。
- 不要为了简单顺序推理创建 subAgent；只有局部任务会明显污染 worker 上下文时才启用。

## 是否替代 `claude -p`

不要把 subAgent 当成 `claude -p` worker 的默认替代品。

`claude -p` 是独立 CLI 进程，适合承担完整阶段：它有独立上下文、独立权限参数、可审计命令、`worker-run-metrics.json`、`worker-cli-output.log` 和明确的文件交接边界。它的缺点是启动成本更高，权限和路径配置更敏感，遇到 Bash 拒绝或 max-turns 截断时需要恢复机制兜底。

subAgent 更适合在一个 worker 内做局部检索或审查：启动轻、上下文隔离感更强、适合并行读材料。但它通常仍依附当前 Claude Code 会话和工具环境，不应该拥有阶段状态机；如果让 subAgent 直接写 handoff、validation 或 workflow state，审计边界会变模糊，也更容易把主 session 拉回业务执行。

推荐策略：

- 默认保持 `主 session -> claude -p worker -> 可选 subAgent`。
- 当阶段只是短小、只读、无文件交接时，可以考虑 subAgent，但这不适用于 requirement-analysis/design-phase 这类完整阶段。
- 当 `claude -p` 主要问题是权限配置，优先修正 allowed tools、路径和 worker prompt；不要用 subAgent 绕过权限问题。
- 当主要问题是 worker 内检索材料太多，再在 `claude -p` worker 内启用 subAgent，把噪声摘要交回父 worker。

## 和主 Session 的关系

推荐结构是：

```text
主 session：状态机、用户交互、外部动作接管、审计摘要
worker：执行一个阶段、读子 skill、写阶段产物、调用 validator
worker 内 subAgent：只做局部检索/审查，把摘要交还 worker
```

这意味着 subAgent 放在 worker 里面是可行的，但不是必须的。真正避免主 session 变长的关键是阶段执行必须在 `claude -p` worker 中完成；subAgent 只是进一步减少 worker 内部上下文压力。
