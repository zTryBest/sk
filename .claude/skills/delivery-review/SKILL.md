---
name: delivery-review
description: >
  当 ReviewAgent 需要汇总全流程产物并形成最终交付审查报告时使用。本 Skill 负责检查 artifact 完整性、
  阶段一致性、残留风险和 `artifacts/08_final_report.md` 输出。
---

# 交付审查 Skill

## 职责

- 读取所有阶段 artifact。
- 检查需求、方案、计划、编码和测试之间是否一致。
- 汇总交付范围、完成项、风险、缺陷和后续建议。
- 输出 `artifacts/08_final_report.md`。

## 禁止

- 不修改需求、方案和代码。
- 不把未通过测试的内容包装成已交付。
- 不隐藏 Human Gate 未确认事项。

## 完成标准

- 所有 artifact 路径和状态清楚。
- 是否可交付有明确结论。
- 残留风险和下一步动作明确。
