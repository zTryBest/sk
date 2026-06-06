# Output Contracts

## 输出文件

设计阶段输出必须保存到需求交接目录，不能保存到 `%USERPROFILE%\.claude\project`、用户 home、临时目录或当前 skill 目录：

```text
<项目根目录>/requirements/<项目名称或平台版本标识>/design-doc.md
<项目根目录>/requirements/<项目名称或平台版本标识>/design-handoff.json
<项目根目录>/requirements/<项目名称或平台版本标识>/design-validation.json
```

## 设计文档核心表

### 实现方式总表

| 来源需求项 | 子能力 | 实现方式分类 | 说明 | 是否需要用户已确认 |
|---|---|---|---|---|

### MCP 检索和证据表

| 证据编号 | 来源需求项 | 平台上下文动作 | 组件 | 段 | 组件版本 | API | 文档版本 | match_level | risk |
|---|---|---|---|---|---|---|---|---|---|

### MCP 调用记录表

| 检索任务编号 | MCP 工具 | 查询词 | 候选数 | 采纳状态 | 采纳/淘汰原因 |
|---|---|---|---|---|---|

### 定制实现表

| 来源需求项 | 子能力 | 定制模块 | 主要职责 | 数据表/配置 | 异常处理 | 测试点 |
|---|---|---|---|---|---|---|

### 外部集成表

| 来源需求项 | 外部系统 | 协议 | 认证 | 请求/响应 | 超时重试 | 回调/回执 | 降级 |
|---|---|---|---|---|---|---|---|

## design-handoff.json

`design-handoff.json` 是后续原型、编码和自测阶段的机器可读入口。Markdown 设计文档用于人工审阅；自动化流水线必须优先读取 JSON。

```json
{
  "schema_version": "1.0",
  "source": {
    "requirement_handoff": "requirement-handoff.json",
    "requirement_doc": "需求分析.md",
    "design_doc": "design-doc.md",
    "generated_at": "",
    "design_status": "final|draft"
  },
  "product": {
    "product_id": "",
    "product_version": "",
    "product_name_aliases": [],
    "component_overrides": {}
  },
  "architecture_decisions": [
    {
      "item": "",
      "decision": "",
      "confirmed": true,
      "rationale": "",
      "risks": []
    }
  ],
  "implementation_classification": [
    {
      "id": "IC-01",
      "from_requirement": "F-01",
      "sub_capability": "",
      "mode": "BASELINE_API_REUSE|CUSTOM_CODE|EXTERNAL_INTEGRATION|HYBRID|NO_API_NEEDED|UNDECIDED",
      "rationale": "",
      "confirmed": true
    }
  ],
  "mcp_search_plan": [
    {
      "task_id": "MCP-01",
      "from_classification": "IC-01",
      "query": "",
      "must_search": true,
      "expected_fields": []
    }
  ],
  "mcp_call_log": [
    {
      "task_id": "MCP-01",
      "tool": "find_apis_for_requirement",
      "request": {},
      "candidate_count": 0,
      "top_candidates": [],
      "decision": "PENDING_USER_CHOICE|SELECTED|REJECTED_SCENE_MISMATCH|REJECTED_FIELD_GAP|REJECTED_RISK|NO_CANDIDATE|NEED_KB_IMPORT",
      "reason": ""
    }
  ],
  "selected_baseline_apis": [
    {
      "task_id": "MCP-01",
      "component_id": "",
      "segment_id": "",
      "component_version": "",
      "method": "",
      "api_path": "",
      "doc_version": "",
      "get_api_detail_called": true,
      "risk": ""
    }
  ],
  "custom_implementation": [
    {
      "from_classification": "IC-02",
      "module": "",
      "responsibility": "",
      "tables_or_config": [],
      "error_handling": [],
      "test_points": []
    }
  ],
  "external_integrations": [
    {
      "from_classification": "IC-03",
      "system": "",
      "protocol": "",
      "auth": "",
      "request_response": "",
      "timeout_retry": "",
      "callback_or_receipt": "",
      "fallback": ""
    }
  ],
  "open_risks": []
}
```

生成规则：

- `implementation_classification` 必须覆盖每个需求项拆出的每个子能力。
- `CUSTOM_CODE`、`EXTERNAL_INTEGRATION`、`HYBRID` 必须分别在 `custom_implementation` 或 `external_integrations` 中有设计说明；不能让 MCP 搜索结果替代定制代码设计。
- `BASELINE_API_REUSE` 和 `HYBRID` 的平台上下文动作必须进入 `mcp_search_plan`，并在 `mcp_call_log` 中留下实际调用记录。
- 选中的基线 API 必须写入 `selected_baseline_apis`，且 `get_api_detail_called=true`。
- 最终版 `design_status=final`，草稿为 `draft`。最终版中不能出现 `UNDECIDED`、`待确认` 或 `[待确认]`。

## Validator

期望校验命令：

```text
python .claude/skills/design-phase/scripts/validate_design.py --handoff <交接目录>/design-handoff.json --output <交接目录>/design-validation.json --project-root <项目根目录>
```

如果当前安装中没有 validator 脚本，不能假装已运行；应明确说明缺少校验脚本，并将阶段标记为不可交接或 `BLOCKED`，除非 orchestrator 提供等价 validator。

校验失败时，读取 `design-validation.json.errors`，修复设计文档和 JSON 后重新运行。不能在校验失败时声明方案设计完成，也不能进入原型、编码或自测阶段。

## 完成检查

- [ ] 已执行 Phase 0，优先读取 `requirement-handoff.json`。
- [ ] 已创建并持续更新 `design-phase-state.md`。
- [ ] 已生成 `design-doc.md`、`design-handoff.json` 和 `design-validation.json`。
- [ ] 三个文件都位于当前项目目录的 `requirements/<项目名称或平台版本标识>/` 下。
- [ ] `design-validation.json.success=true`。
- [ ] 平台和版本已确认。
- [ ] 架构和中间件已经确认，或用户明确要求全自动。
- [ ] 已调用 `list_products` 校验平台存在。
- [ ] 已调用 `list_product_components` 确认组件范围。
- [ ] 已把每个需求项拆成执行动作和平台上下文动作。
- [ ] 已为每个子能力标注实现方式分类。
- [ ] 每个平台上下文动作都生成了明确的 MCP 检索任务。
- [ ] 每个 MCP 检索任务都调用了 `find_apis_for_requirement`。
- [ ] 每个最终 API 都调用了 `get_api_detail`。
- [ ] MCP 调用记录、候选、采纳/淘汰原因已经写入文档。
- [ ] `CUSTOM_CODE`、`EXTERNAL_INTEGRATION`、`HYBRID` 子能力都有非 MCP 设计说明。
- [ ] 没有用外部动作或功能标题直接作为 MCP 查询词。
- [ ] 没有因为外部动作查不到 API 就判定整个需求不需要基线组件。
- [ ] 所有风险都展示给用户并被确认。
- [ ] 没有使用旧版搜索类或候选提交类 MCP 工具。
- [ ] 没有编造组件/API。
