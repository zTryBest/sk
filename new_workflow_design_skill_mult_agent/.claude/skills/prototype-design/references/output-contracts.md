# 输出契约

原型设计阶段的产物：

```text
artifacts/03_prototype.html
artifacts/03_prototype_screenshots/   (可选)
```

## HTML 文件规范

单文件自包含 HTML，结构：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project_name} - 原型</title>
  <style>
    /* 所有 CSS 内联 */
  </style>
</head>
<body>
  <!-- 页面内容，使用 data-requirement 标注 -->
  <div data-page="login" data-requirement="F-01">...</div>
  <div data-page="list" data-requirement="F-02" style="display:none">...</div>
  
  <script>
    // 所有 JS 内联：路由、交互、模拟数据
  </script>
</body>
</html>
```

## 标注规范

- `data-page="pagename"` — 页面标识。
- `data-requirement="F-XX"` — 对应需求编号。
- `data-api="POST /api/v1/xxx"` — 对应 API（如方案中已定义）。

## 截图目录

```text
artifacts/03_prototype_screenshots/
├── page_01_{pagename}.png
├── page_02_{pagename}.png
└── overview.png              (可选：全部页面缩略图拼接)
```

截图分辨率：1280x800（桌面）。

## 完成检查

- [ ] HTML 文件浏览器可直接打开。
- [ ] 每个功能需求有对应页面或交互区域。
- [ ] 页面间导航流程覆盖主路径。
- [ ] 表单字段与方案中的 API 字段对应。
- [ ] `data-requirement` 标注完整。
- [ ] 无外部依赖（CDN、本地文件引用）。
- [ ] 截图成功（或标注为 open_decisions）。
