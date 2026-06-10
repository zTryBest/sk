"""
Backend scaffold MCP server.

封装公司 SpringBoot 脚手架生成服务:
- GET /v1/frame/info  → 完整表单 schema (baseInfos + configInfo + defaultValue + type)
- POST /v1/frame/frame → 接收 FrameRequestDTO, 返回 zip 流

HTTP transport, 部署在局域网共享机器, 团队通过 mcp HTTP transport 连接。

环境变量:
  SCAFFOLD_BACKEND_URL  SpringBoot 服务 base URL, 默认 http://127.0.0.1:8888
  MCP_HTTP_PORT          本 MCP server 监听端口, 默认 8001
  MCP_HTTP_HOST          监听地址, 默认 0.0.0.0 (允许局域网访问)
"""
from fastmcp import FastMCP
import httpx
import zipfile
import io
import os
import re
from pathlib import Path

mcp = FastMCP("scaffold")

BASE = os.getenv("SCAFFOLD_BACKEND_URL", "http://127.0.0.1:8888")


# ---------- 工具 1: 拉取完整表单 schema ----------

@mcp.tool()
def get_form_schema() -> dict:
    """
    实时拉取 SpringBoot 脚手架表单 schema。

    用途:
    - Orchestrator 在编码阶段开头调用, 拿到 baseInfos 9 项 + configInfo 7 类的完整结构,
      按 schema 动态生成 AskUserQuestion 收集用户配置。
    - 每个 baseInfos 字段含 defaultValue, 可作为推荐项。
    - 每个 configInfo 字段含 type (radio/checkbox/cascader-multi) 和 options 候选清单。

    返回示例:
    {
      "code": "0",
      "data": {
        "baseInfos": [
          {"label":"组件版本号","value":"version","defaultValue":"2.0-SNAPSHOT","type":"input",...},
          ...
        ],
        "configInfo": [
          {"label":"数据库","value":"database","type":"radio","options":[...],...},
          ...
        ]
      }
    }

    错误返回:
      {"status":"error","error_code":"SCHEMA_FETCH_FAILED","message":"..."}
    """
    try:
        r = httpx.get(f"{BASE}/v1/frame/info", timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error_code": "SCHEMA_FETCH_FAILED",
            "message": str(e),
        }


# ---------- 工具 2: 提前校验命名 ----------

@mcp.tool()
def validate_params(packageName: str, componentId: str) -> dict:
    """
    提前校验 packageName 和 componentId 是否符合服务端正则,
    避免下载时才被 SpringBoot 拒绝。

    SpringBoot 端规则:
    - packageName: ^[a-z.]*$ 且至少一个点 (如 com.aries.jc.sc)
    - componentId: ^[a-z]+[a-zA-Z]*$ (如 patpps)
    """
    errors = []
    if not re.match(r"^[a-z.]+$", packageName) or "." not in packageName:
        errors.append("packageName 仅含小写字母和点, 且至少一个点 (如 com.aries.jc.sc)")
    if not re.match(r"^[a-z]+[a-zA-Z]*$", componentId):
        errors.append("componentId 以小写字母开头, 仅含字母 (如 patpps)")
    return {"valid": not errors, "errors": errors}


# ---------- 内部: 把 config dict 翻译成 FrameRequestDTO.configInfo (List<LabelDTO>) ----------

def _config_to_label_dtos(config: dict) -> list[dict]:
    """
    把扁平 config dict 翻译成 FrameRequestDTO.configInfo 的 LabelDTO 列表。

    规则 (与团队约定):
    - radio 单选:        {"label": <field>, "has": true, "value": <选中 value>}
    - checkbox 多选:      {"label": <field>, "has": true, "value": "v1,v2,v3"} (逗号拼)
    - cascader-multi:    {"label": <field>, "has": true, "value": "p1,c1;p1,c2;p2,c1"}
                         (每组 父,子 用逗号; 多组用分号分隔)
    - 用户未选 (空或 None): 跳过, 不进 LabelDTO 列表

    config 输入示例:
      {
        "database": "mysql",                                    # radio
        "cache": "redisson",                                    # radio
        "mq": ["kafka", "rabbitMq"],                            # checkbox
        "reference": [["consul","bic"], ["consul","xauthc"]],   # cascader-multi
        "javaVersion": "11",                                    # radio
        "basicFeatures": ["cloudstore"],                        # checkbox
        "controller": [],                                       # checkbox 留空
      }
    """
    result = []
    for field, value in config.items():
        if value is None or value == "" or value == []:
            continue

        if isinstance(value, str):
            # radio
            result.append({"label": field, "has": True, "value": value})
        elif isinstance(value, list):
            if not value:
                continue
            # 判断 cascader-multi (元素是 list) 还是 checkbox (元素是 str)
            if all(isinstance(item, list) for item in value):
                # cascader-multi: [["consul","bic"], ["consul","xauthc"]]
                joined = ";".join(",".join(str(x) for x in group) for group in value)
                result.append({"label": field, "has": True, "value": joined})
            else:
                # checkbox: ["kafka", "rabbitMq"]
                joined = ",".join(str(x) for x in value)
                result.append({"label": field, "has": True, "value": joined})
        # 其他类型 (数字等) 转字符串
        else:
            result.append({"label": field, "has": True, "value": str(value)})

    return result


# ---------- 工具 3: 生成脚手架并解压 ----------

@mcp.tool()
def generate_backend(
    version: str,
    packageName: str,
    componentId: str,
    serviceId: list[str],
    port: str,
    errorCode: str,
    dependenciesVersion: str,
    email: str,
    author: str,
    config: dict,
    output_path: str = "workspace/backend",
    overwrite: bool = False,
) -> dict:
    """
    生成 SpringBoot 后端脚手架, 下载 zip 并解压到 output_path。
    Binary 在 MCP server 内部处理, LLM 上下文只接收结构化元信息。

    必填参数 (baseInfos):
      version:              组件版本号, 如 "2.0-SNAPSHOT"
      packageName:          Java 包路径, 如 "com.aries.jc.sc"  (正则 ^[a-z.]*$)
      componentId:          组件标识, 如 "patpps"               (正则 ^[a-z]+[a-zA-Z]*$)
      serviceId:            服务段名列表, 如 ["patpps"]          (custominput 类型, 可多个)
      port:                 服务端口, 如 "17000"
      errorCode:            错误码, 如 "0x160a"
      dependenciesVersion:  SpringBoot 父依赖版本, 如 "3.4.3"
      email:                作者邮箱
      author:               作者名

    必填参数 (configInfo, 按 info schema 字段名):
      config: dict, 示例:
        {
          "database": "mysql",                                  # radio 单选
          "cache": "redisson",                                  # radio 单选
          "mq": ["kafka"],                                      # checkbox 多选
          "reference": [["consul","bic"]],                      # cascader-multi 父子路径列表
          "javaVersion": "11",                                  # radio 单选
          "basicFeatures": ["cloudstore"],                      # checkbox 多选
          "controller": ["user"],                               # checkbox 多选
        }
      未选项目可省略 key 或传空。

    可选参数:
      output_path: 解压目标 (相对调用方 CWD), 默认 "workspace/backend"
      overwrite:   目标非空时是否覆盖, 默认 False

    成功返回:
      {"status":"ok", "output_path", "files_created", "main_class",
       "build_command", "next_steps":[...]}

    失败返回:
      {"status":"error", "error_code", "message"}
      error_code 可能值:
        INVALID_PARAMS / TARGET_NOT_EMPTY / DOWNLOAD_FAILED /
        BACKEND_VALIDATION / ZIP_CORRUPTED
    """
    v = validate_params(packageName=packageName, componentId=componentId)
    if not v["valid"]:
        return {
            "status": "error",
            "error_code": "INVALID_PARAMS",
            "message": "; ".join(v["errors"]),
        }

    target = Path(output_path).resolve()
    if target.exists() and any(target.iterdir()) and not overwrite:
        return {
            "status": "error",
            "error_code": "TARGET_NOT_EMPTY",
            "message": f"{output_path} 非空, 传 overwrite=True 强制覆盖",
        }
    target.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": version,
        "packageName": packageName,
        "componentId": componentId,
        "serviceId": serviceId,
        "port": port,
        "errorCode": errorCode,
        "dependenciesVersion": dependenciesVersion,
        "email": email,
        "author": author,
        "configInfo": _config_to_label_dtos(config),
    }

    try:
        r = httpx.post(f"{BASE}/v1/frame/frame", json=payload, timeout=60)
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        try:
            err_body = e.response.json()
        except Exception:
            err_body = e.response.text[:500]
        return {
            "status": "error",
            "error_code": "BACKEND_VALIDATION",
            "message": f"HTTP {e.response.status_code}: {err_body}",
        }
    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error_code": "DOWNLOAD_FAILED",
            "message": str(e),
        }

    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            zf.extractall(target)
            files = zf.namelist()
    except zipfile.BadZipFile as e:
        return {
            "status": "error",
            "error_code": "ZIP_CORRUPTED",
            "message": str(e),
        }

    return {
        "status": "ok",
        "output_path": str(target),
        "files_created": len(files),
        "framework": "spring-boot",
        "framework_parent_version": dependenciesVersion,
        "main_class": f"{packageName}.Application",
        "build_command": "mvn compile",
        "next_steps": [
            f"cd {output_path}",
            "配置 src/main/resources/application.yml",
            "mvn compile",
        ],
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("MCP_HTTP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_HTTP_PORT", "8001")),
        path="/mcp",
    )
