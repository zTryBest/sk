# 输出契约

前端编码阶段产物：

```text
artifacts/06_frontend_report.md
workspace/frontend/                    (代码)
```

## 报告结构

```markdown
# 前端编码报告

## 概要

- 项目名称：
- 技术栈：
- 完成时间：

## 任务完成情况

| 任务 ID | 标题 | 状态 | 说明 |
|---------|------|------|------|
| FE-01 | ... | completed | ... |
| FE-02 | ... | completed | ... |

## 消费的接口

| Contract ID | 方法 | 路径 | 使用位置 |
|-------------|------|------|---------|
| API-01 | POST | /api/v1/users | LoginPage |

## 页面清单

| 页面 | 路由 | 对应需求 | 状态 |
|------|------|---------|------|
| 登录页 | /login | F-01 | 完成 |

## 代码结构

```text
workspace/frontend/
├── src/
│   ├── pages/
│   ├── components/
│   ├── services/
│   ├── store/
│   └── utils/
├── public/
├── package.json
└── README.md
```

## 构建结果

- 构建状态：通过/失败
- Lint：X warnings / Y errors
- TypeCheck：通过/失败

## Issues Found

| severity | category | title | affected |
|----------|----------|-------|----------|
| ... | ... | ... | ... |

## 备注

{其他需要说明的内容}
```

## 写入规则

- report 使用 markdown 格式。
- 代码输出到 `workspace/frontend/`。
- 不在 `artifacts/` 目录放代码文件。
- 不修改其他 artifact。

## 完成检查

- [ ] 所有分配任务都有对应页面/组件实现。
- [ ] 构建通过。
- [ ] API 消费匹配 interface_contracts（路径、方法、请求/响应）。
- [ ] 报告完整（任务状态、接口列表、构建结果、issues）。
- [ ] 代码在 workspace/frontend/ 下。
