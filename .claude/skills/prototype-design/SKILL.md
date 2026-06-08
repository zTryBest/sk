---
name: prototype-design
description: >
  当 PrototypeAgent 需要根据 `artifacts/01_requirement.json` 和 `artifacts/02_solution.json`
  生成可审阅 HTML 原型时使用。本 Skill 只负责原型设计和 `artifacts/03_prototype.html` 输出。
---

# 原型设计 Skill

## 职责

- 读取需求和方案。
- 设计核心页面、交互状态、表单、列表、详情、错误提示和空状态。
- 输出可直接打开审阅的 `artifacts/03_prototype.html`。
- 保持原型服务于需求确认和研发对齐，不写真实业务代码。

## 禁止

- 不修改需求和方案 artifact。
- 不调用后端服务。
- 不生成前端工程。
- 不跳过 Human Gate。

## 输入

```text
artifacts/01_requirement.json
artifacts/02_solution.json
```

## 输出

```text
artifacts/03_prototype.html
```

HTML 应包含：
- 页面结构。
- 核心用户流程。
- 关键字段和校验提示。
- 加载、空数据、错误和成功状态。
- 与方案中 Gateway API 的对应关系说明。

## 完成标准

- 原型覆盖主要功能路径。
- 页面内容与需求和方案一致。
- 文件可在浏览器中打开。
- 未确认的交互点以明显注释或占位说明列出。
