---
name: delivery-review
description: >
  当 ReviewAgent 需要汇总全流程产物并形成最终交付审查报告时使用。本 Skill 负责检查 artifact 完整性、
  阶段一致性、残留风险和 `artifacts/08_final_report.md` 输出；不负责编码修复或需求变更。
---

# 交付审查 Skill

本 Skill 说明"如何做交付前的最终审查"。ReviewAgent 负责调用本 Skill，Orchestrator 在 pipeline 最后阶段调度。

## 阶段边界

应该做：
- 读取所有 artifact（01-07）。
- 读取 `.ai-dev/state.json`、`decision-log.json`、`issue-log.json`。
- 检查产物完整性和阶段间一致性。
- 验证需求 → 方案 → 任务 → 代码 → 测试的追溯链。
- 汇总残留风险和未解决 issue。
- 产出 `artifacts/08_final_report.md`。

禁止做：
- 不修改任何已有 artifact。
- 不写代码。
- 不修改 state.json 或其他状态文件。
- 不调度其他 Agent。
- 不写流程控制文件。

## 输入

必须读取：

```text
artifacts/01_requirement.json
artifacts/02_solution.json
artifacts/03_prototype.html         (如存在)
artifacts/04_plan.json
artifacts/05_backend_report.md
artifacts/06_frontend_report.md
artifacts/07_test_report.md
.ai-dev/state.json
.ai-dev/decision-log.json
.ai-dev/issue-log.json
```

## 审查流程

### 1. 产物完整性检查

验证所有必须 artifact 存在且格式正确：

| Artifact | 必须 | 检查项 |
|----------|------|--------|
| 01_requirement.json | 是 | JSON 可解析，status=final |
| 02_solution.json | 是 | JSON 可解析，status=final |
| 03_prototype.html | 条件 | HTML 可渲染（如阶段未 skip） |
| 04_plan.json | 是 | JSON 可解析，status=final |
| 05_backend_report.md | 是 | 非空，有任务完成表 |
| 06_frontend_report.md | 是 | 非空，有任务完成表 |
| 07_test_report.md | 是 | 非空，有测试汇总表 |

### 2. 追溯链验证

检查从需求到测试的完整追溯：

```
每个 F-xx（功能需求）
  → 对应 IC-xx（实现方式分类） in 02_solution.json
  → 对应 BE-xx / FE-xx（任务） in 04_plan.json
  → 对应代码实现 in 05/06_report
  → 对应测试覆盖 in 07_test_report
```

输出追溯矩阵：

| 需求 | 方案覆盖 | 任务覆盖 | 后端实现 | 前端实现 | 测试覆盖 | 完整性 |
|------|---------|---------|---------|---------|---------|--------|
| F-01 | IC-01 | BE-01,FE-01 | YES | YES | YES | 完整 |
| F-02 | IC-02 | BE-02 | YES | N/A | YES | 完整 |

### 3. 决策记录审查

从 `decision-log.json` 汇总：
- 关键决策清单。
- REVISE 次数和原因。
- 是否有未执行的决策。

### 4. Issue 审查

从 `issue-log.json` 汇总：
- 已解决 issue 清单。
- 未解决 issue 及其严重程度。
- Accepted risk 清单。

### 5. 风险评估

综合分析残留风险：
- 测试中发现的未修复缺陷。
- 未解决的 issue。
- 覆盖率缺口。
- 已知的技术债务。
- accepted risk 的长期影响。

### 6. 产出报告

输出 `artifacts/08_final_report.md`。

## 完成标准

ReviewAgent 完成的条件：
- 所有必须 artifact 已检查。
- 追溯矩阵已输出。
- 残留风险已汇总。
- `artifacts/08_final_report.md` 已产出。

交付审查不判断"是否可以上线"，只客观呈现状态。上线决策由用户通过最终 Human Gate 做出。
