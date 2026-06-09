# 输出契约

后端编码阶段产物：

```text
artifacts/05_backend_report.md
workspace/backend/                    (代码)
```

## 报告结构

```markdown
# 后端编码报告

## 概要

- 项目名称：
- 技术栈：
- 完成时间：

## 任务完成情况

| 任务 ID | 标题 | 状态 | 说明 |
|---------|------|------|------|
| BE-01 | ... | completed | ... |
| BE-02 | ... | completed | ... |

## 实现的接口

| Contract ID | 方法 | 路径 | 状态 |
|-------------|------|------|------|
| API-01 | POST | /api/v1/users | 已实现 |

## 代码结构

```text
workspace/backend/
├── src/
│   ├── controllers/
│   ├── services/
│   ├── models/
│   ├── repositories/
│   └── config/
├── tests/
├── package.json / pom.xml / ...
└── README.md
```

## 编译和测试结果

- 编译状态：通过/失败
- 单元测试：X passed / Y failed

## Issues Found

| severity | category | title | affected |
|----------|----------|-------|----------|
| ... | ... | ... | ... |

## 备注

{其他需要说明的内容}
```

## 写入规则

- report 使用 markdown 格式。
- 代码输出到 `workspace/backend/`。
- 不在 `artifacts/` 目录放代码文件。
- 不修改其他 artifact。

## 完成检查

- [ ] 所有分配任务都有对应代码实现。
- [ ] 编译通过。
- [ ] interface_contracts 中的 API 路径、方法、请求/响应格式准确匹配。
- [ ] 报告完整（任务状态、接口列表、编译结果、issues）。
- [ ] 代码在 workspace/backend/ 下。
