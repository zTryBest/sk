---
name: testing
description: >
  当 TestAgent 需要基于需求、方案、计划、后端报告和前端报告执行测试时使用。本 Skill 负责测试执行、
  缺陷归类和 `artifacts/07_test_report.md` 输出。
---

# 测试 Skill

## 职责

- 读取 `01_requirement.json`、`02_solution.json`、`04_plan.json`、`05_backend_report.md` 和 `06_frontend_report.md`。
- 执行可用的后端、前端和集成测试。
- 对失败项按需求偏差、方案偏差、编码缺陷、环境问题分类。
- 输出 `artifacts/07_test_report.md`。

## 禁止

- 不新增需求。
- 不直接修改代码，除非 Main Agent 明确安排修复轮次。
- 不掩盖失败测试。

## 完成标准

- 测试命令、结果和失败原因记录完整。
- 阻塞缺陷和非阻塞风险区分清楚。
- 报告给出是否可交付的测试结论。
