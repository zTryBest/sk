---
name: pencil
description: >
  Two-round UI prototype workflow using Pencil.dev via Claude Code + Pencil MCP.
  Round 1 (post-requirement-analysis): low-fidelity mockups for business confirmation.
  Round 2 (post-design-phase): high-fidelity designs from full page specs.
  Outputs .pen design files + PNG previews. Excalidraw fallback for hand-drawn wireframes.
  This skill assumes Pencil Desktop is running on Windows.
---

# Pencil: AI-Powered UI Prototype Generator

## Purpose

Pencil operates in **two rounds** at different stages of the workflow:

```
需求分析 → Pencil Round 1 (低保真确认稿) → 业务确认
                                                    ↓
                                              方案设计 → Pencil Round 2 (高保真设计稿)
                                                              ↓
                                                           开发
```

| | Round 1（确认稿） | Round 2（设计稿） |
|---|---|---|
| **输入来源** | requirement-analysis 产出的功能项 | design-phase Phase 4 的完整页面规格 |
| **目的** | 给业务方确认"是不是这个意思" | 给开发提供精确的 UI 参照 |
| **精度** | 低保真：页面结构 + 关键元素 + 主流程 | 高保真：完整 UI 清单 + 交互 + API |
| **API 依赖** | 不需要（网关 API 尚未设计） | 需要（API 路径已确定） |
| **路由** | 不需要（路由尚未确定） | 需要 |

## Environment Detection

生成设计稿之前，按顺序检测 Pencil 环境。**不假设路径，逐级 fallback**。

### Step 1: 查找 Pencil 桌面应用

```cmd
:: 先检查是否已经在运行（Windows）
tasklist | findstr /i "pencil.exe" && echo RUNNING

:: 再查默认安装路径
dir "%LOCALAPPDATA%\Programs\pencil\pencil.exe" 2>nul && echo FOUND
```

- 已运行 → 跳到 Step 2
- 找到但未运行 → 启动：`start "" "%LOCALAPPDATA%\Programs\pencil\pencil.exe"`
- 未找到 → 继续 Step 2（Pencil 可能从其他路径安装，MCP server 仍可达）

### Step 2: 测试 MCP Server 连接

Pencil Desktop 启动时会自动注册 MCP server。测试是否可达：

```cmd
:: 定位 MCP server（随 Pencil Desktop 安装）
set "MCP_SERVER=%LOCALAPPDATA%\Programs\pencil\resources\app.asar.unpacked\out\mcp-server-windows-x64.exe"

:: 测试连接
echo {"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}} | "%MCP_SERVER%" --app desktop 2>&1 | findstr "result"
```

结果判断：
- 输出含 `"result"` → MCP server 连上了 Pencil 桌面应用，可以继续
- 输出含 `app connection is required` → MCP server 存在但 Pencil 桌面应用没运行 → 进 Step 3
- `mcp-server-windows-x64.exe` 不存在 → 进 Step 3

### Step 3: 都不行 → 提示用户

> Pencil 未启动或未安装。请：
> 1. 下载 Pencil Desktop for Windows：https://pencil.dev/downloads（`Pencil-win-x64.exe`）
> 2. 安装并启动 Pencil Desktop
> 3. 确认窗口显示且系统托盘有 Pencil 图标后重试

### Step 4: Claude Code MCP 配置（仅首次）

Pencil 桌面应用启动后通常会**自动注册** MCP server。如果 Claude Code 仍未识别 Pencil 工具：

```bash
claude mcp add pencil -- "%MCP_SERVER%" --app desktop
```

或检查已有配置：`claude mcp list | grep pencil`

### Claude Code 认证

```bash
set ANTHROPIC_API_KEY=sk-ant-...
# 或使用第三方代理：
set ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
```

## Workflow

### Phase 0: Determine Which Round

| 上游文档 | Round | 文档路径示例 |
|----------|-------|-------------|
| 需求文档 | Round 1 | `%USERPROFILE%\.claude\requirements\<platform>\<feature>.md` |
| 设计文档 | Round 2 | `%USERPROFILE%\.claude\design\<platform>\<feature>-设计文档.md` |

> **WSL 用户注意**：WSL 中的路径在 Windows 下对应 `/mnt/c/Users/<username>/... Hermes 文档在 WSL 的 `~/.claude/` 目录，对应 Windows 路径 `\\wsl$\<distro>\home\<user>\.claude\`。

---

## Round 1: Low-Fidelity Confirmation（低保真确认稿）

### R1 Step 1: Load Context

1. 加载需求文档，提取：
   - 平台 + 版本
   - 功能清单（F-01, F-02, ...）及其描述
   - 验收标准（Given/When/Then）
   - 用户角色
2. 识别哪些功能项需要页面。不需要页面的（纯后端逻辑、定时任务等）跳过。

### R1 Step 2: Page Mapping

将功能项映射到页面。Round 1 的页面是**推断**的（尚未有正式路由）：

```
| 需求功能 | 推断页面 | 说明 |
|----------|---------|------|
| F-01 短信平台配置 | 短信配置页 | 表单页 |
| F-02 模板管理 | 模板列表页 + 新增/编辑模板弹窗 | 列表+弹窗 |
```

### R1 Step 3: Confirm Page Mapping

询问用户确认页面映射是否合理。用户可能纠正或补充。

### R1 Step 4: Generate Round 1 Designs

使用 Pencil MCP 工具生成低保真页面。Round 1 prompt 聚焦**业务理解**，不需要技术细节：

- 用**业务语言**描述，不用技术术语
- 描述**用户看到什么、能做什么**
- 不必精确到每个 UI 元素的状态细节
- 不含 API 路径、路由等技术信息

**Pencil MCP 工具调用顺序**：
1. `open_document` — 创建新 .pen 文件
2. `get_editor_state({ include_schema: true })` — 获取编辑器状态
3. `batch_design` — 分批构建设计（结构 → 内容 → 细节）
4. `export_nodes` — 导出 PNG
5. `get_screenshot` — 可选，视觉检查

### R1 Step 5: Output

输出目录（Windows 路径）：
```
%USERPROFILE%\.claude\output\prototype\<platform>\<feature>\
├── <PageName>.pen
├── <PageName>.png
└── README.md
```

README.md 包含页面清单和业务方确认要点。

### R1 Step 6: Post-Confirmation

业务方确认后，记录反馈，带着确认结果进入方案设计阶段。

---

## Round 2: High-Fidelity Design（高保真设计稿）

### R2 Step 1: Load Context

1. 加载设计文档，提取 Phase 4 前端页面设计部分。
2. 识别所有页面：名称、路由、类型、UI 元素清单、交互流程、API 依赖。

### R2 Step 2: Confirm Before Generating

展示即将生成的页面清单，用户确认后开始。

### R2 Step 3: Generate Round 2 Designs

Round 2 prompt 包含**完整的技术细节**：
- 路由路径
- 完整 UI 元素清单（含初始状态）
- 交互流程（加载 → 操作 → 反馈）
- API 依赖（网关路径）
- Loading / Empty / Error 状态

**Pencil MCP 工具调用顺序**（同 Round 1）

### R2 Step 4: Output

输出目录（Windows 路径）：
```
%USERPROFILE%\.claude\output\design\<platform>\<feature>\
├── <PageName>.pen
├── <PageName>.png
└── README.md
```

---

## Output Directory Convention

```
%USERPROFILE%\.claude\output\
├── prototype\<platform>\<feature>\   ← Round 1 低保真确认稿
└── design\<platform>\<feature>\      ← Round 2 高保真设计稿
```

WSL 用户对应路径：`/mnt/c/Users/<username>/.claude/output/`

---

## Fallback: Excalidraw

如果 Pencil Desktop 未运行或 MCP 不可用，使用 `excalidraw` skill 生成手绘风格线框图。

---

## Pitfalls

- **Pencil Desktop 必须运行** — 生成设计前确认 Pencil Desktop 窗口已打开（可最小化）
- **Round 1 ≠ Round 2** — 两轮输入不同，不要用 Round 2 的详细规格去生成 Round 1 的确认稿
- **Round 1 用业务语言** — 业务方看不懂 API 路径、组件名称
- **Round 1 标注推断** — 明确哪些是 AI 推断的，哪些是需求文档明确写的
- **MCP 断开** — 如果 Pencil Desktop 窗口关闭，MCP 连接会断开。重新打开 Pencil 后重试
- **--app desktop** — MCP server 必须用 `--app desktop`，不是 `--app pencil`
- **Windows 路径** — MCP server 的 exe 路径在 `%LOCALAPPDATA%\Programs\pencil\resources\app.asar.unpacked\out\`
- **WSL 路径转换** — WSL 中的 `/home/user/` 对应 Windows `\\wsl$\<distro>\home\user\`
- **确认后再进下一阶段** — Round 1 必须等业务方确认后才进入方案设计
