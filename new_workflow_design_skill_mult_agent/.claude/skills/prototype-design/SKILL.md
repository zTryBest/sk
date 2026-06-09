---
name: prototype-design
description: >
  当 PrototypeAgent 需要根据 `artifacts/01_requirement.json` 和 `artifacts/02_solution.json`
  生成可审阅 HTML 原型和截图时使用。本 Skill 只负责原型设计和 `artifacts/03_prototype.html` 输出；
  不负责需求、方案、编码、测试或流程调度。
---

# 原型设计 Skill

本 Skill 说明"UI 原型怎么做"。PrototypeAgent 负责调用本 Skill，Orchestrator 负责阶段顺序和 Human Gate。

## 阶段边界

应该做：
- 读取 `artifacts/01_requirement.json` 和 `artifacts/02_solution.json`。
- 生成自包含的 HTML 原型文件（HTML + CSS + JS 单文件）。
- 覆盖所有功能需求的页面和交互流程。
- 使用 Playwright MCP 截图保存为 PNG。
- 为每个 UI 元素标注对应的需求 ID（data-requirement 属性）。
- 对无法确定的 UI 决策输出 `open_decisions`。

禁止做：
- 不写后端代码。
- 不修改需求或方案 artifact。
- 不做架构设计决策。
- 不调度其他 Agent。
- 不写流程控制文件。

## 输入

必须读取：

```text
artifacts/01_requirement.json
artifacts/02_solution.json
```

可以读取：
- Human Gate 对原型的修改意见。
- `artifacts/02_solution.json` 中的 `frontend_design` 部分。

## 设计流程

### 1. 需求加载

从 `01_requirement.json` 提取：
- 功能需求列表及其交互描述。
- 用户角色和权限。
- 业务规则（影响 UI 展示逻辑）。

从 `02_solution.json` 提取：
- `frontend_design` 中的页面规划。
- `api_design` 中的接口（确定数据展示字段）。
- 导航和页面流转。

### 2. 页面规划

输出页面清单：

| 页面 | 对应需求 | 主要功能 | 入口 |
|------|---------|---------|------|
| 登录页 | F-01 | 用户认证 | URL 直接访问 |
| 列表页 | F-02 | 数据查看 | 导航菜单 |
| ... | ... | ... | ... |

### 3. 原型实现

生成单文件 HTML 原型：
- 使用 HTML5 + CSS3 + 原生 JS（不依赖外部 CDN）。
- 页面间通过 hash 路由或 tab 切换模拟导航。
- 表单使用真实字段名（与 API 设计对应）。
- 列表使用模拟数据展示布局效果。
- 交互状态通过 JS 切换（按钮点击、弹窗、表单验证提示）。
- 响应式布局（适配桌面和移动端）。

### 4. 需求追溯标注

每个功能相关的 UI 元素添加 `data-requirement` 属性：

```html
<form data-requirement="F-01">
  <input name="username" data-requirement="F-01" />
  <button type="submit" data-requirement="F-01">登录</button>
</form>
```

### 5. 截图

使用 Playwright MCP 工具：
1. 在本地打开 HTML 文件。
2. 对每个主要页面/状态截图。
3. 保存到 `artifacts/03_prototype_screenshots/` 目录。

如果 Playwright MCP 不可用，标注为 `open_decisions` 让用户手动截图。

### 6. 样式规范

- 使用中性配色（灰白为主，蓝色强调色）。
- 字体：系统默认字体栈。
- 间距和尺寸保持一致性。
- 不追求精美视觉，重点是布局和信息架构的准确性。

## 输出

必须输出：

```text
artifacts/03_prototype.html
```

可选输出（如 Playwright 可用）：

```text
artifacts/03_prototype_screenshots/
├── page_01_login.png
├── page_02_list.png
└── ...
```

## 完成标准

只有满足以下条件，PrototypeAgent 才能把本阶段标为 `final`：
- 已读取并使用需求和方案 artifact。
- 每个功能需求至少有一个对应页面或交互。
- HTML 文件可在浏览器中直接打开并正确渲染。
- 页面间导航流程完整。
- 表单字段与 API 设计中的字段名对应。
- 无关键 `open_decisions`（如布局、导航等 UI 核心决策）。

否则必须输出 `draft` 并说明 `open_decisions`。
