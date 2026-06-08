---
name: frontend-coding
description: >
  当 FrontendAgent 需要根据 `artifacts/04_plan.json` 和 `artifacts/03_prototype.html`
  完成前端编码时使用。本 Skill 负责 `workspace/frontend/` 实现和 `artifacts/06_frontend_report.md` 输出。
---

# 前端编码 Skill

## 职责

- 读取计划、方案和原型。
- 在 `workspace/frontend/` 中实现前端页面和交互。
- 对接计划中定义的 Gateway API。
- 运行可用构建和测试命令。
- 输出 `artifacts/06_frontend_report.md`。

## 禁止

- 不修改需求、方案和计划。
- 不直接调用 baseline API，前端只调用 Gateway API。
- 不写后端代码。
- 不大范围重构无关工程结构。

## 完成标准

- 主要页面和交互已实现。
- 接口调用与 `04_plan.json` 一致。
- 已运行可用构建/测试命令。
- 已输出前端报告。
