"""
Backend scaffold MCP server.

封装公司 SpringBoot 脚手架生成服务 (POST /v1/frame/frame)。
HTTP transport，部署在局域网共享机器，团队通过 mcp HTTP transport 连接。

环境变量:
  SCAFFOLD_BACKEND_URL  SpringBoot 服务 base URL，默认 http://127.0.0.1:8888
  MCP_HTTP_PORT          本 MCP server 监听端口，默认 8001
  MCP_HTTP_HOST          监听地址，默认 0.0.0.0 (允许局域网访问)

启动:
  pip install -r requirements.txt
  python scaffold_mcp.py

团队成员注册:
  claude mcp add --scope user --transport http scaffold http://<局域网IP>:8001/mcp
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


@mcp.tool()
def list_middleware_options() -> dict:
    """
    列出脚手架可选中间件清单 (configInfo 字段候选)。
    实时从 SpringBoot GET /api/options 拉取，保证清单与服务端同步。

    返回格式 (由 SpringBoot 服务定义):
      {"options": [{"label": "Redis", "value": "redis"}, ...]}
    """
    try:
        r = httpx.get(f"{BASE}/api/options", timeout=10)
        if r.status_code == 404:
            return {
                "status": "error",
                "error_code": "NOT_IMPLEMENTED",
                "message": "SpringBoot /api/options 接口未实现，请联系后端同学添加"
            }
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error_code": "OPTIONS_FETCH_FAILED",
            "message": str(e)
        }


@mcp.tool()
def validate_params(package_name: str, component_id: str) -> dict:
    """
    提前校验 packageName 和 componentId 是否符合服务端正则。
    SpringBoot 端规则:
      - packageName: ^[a-z.]*$ 且至少一个点
      - componentId: ^[a-z]+[a-zA-Z]*$
    """
    errors = []
    if not re.match(r"^[a-z.]+$", package_name) or "." not in package_name:
        errors.append("packageName 仅含小写字母和点，且至少一个点 (如 com.company.app)")
    if not re.match(r"^[a-z]+[a-zA-Z]*$", component_id):
        errors.append("componentId 以小写字母开头，仅含字母 (如 patpps)")
    return {"valid": not errors, "errors": errors}


@mcp.tool()
def generate_backend(
    component_id: str,
    package_name: str,
    service_ids: list[str],
    port: str,
    error_code: str,
    author: str,
    email: str,
    middlewares: list[dict],
    version: str = "2.0-SNAPSHOT",
    dependencies_version: str = "3.2.5.RELEASE",
    output_path: str = "workspace/backend",
    overwrite: bool = False
) -> dict:
    """
    生成 SpringBoot 后端脚手架，下载 zip 并解压到 output_path。
    Binary 在 MCP server 内部处理，LLM 上下文只接收结构化元信息。

    必填参数:
      component_id: 组件 ID，如 "patpps"
      package_name: Java 包路径，如 "com.company.demo"
      service_ids: 服务段名列表，从 list_middleware_options/或 /api/options 获取候选
      port: 服务端口，如 "17000"
      error_code: 错误码起始值，如 "0x160a"
      author: 作者名 (建议从 git config user.name 拿)
      email: 作者邮箱 (建议从 git config user.email 拿)
      middlewares: 中间件配置列表，[{"label":"Redis","has":true,"value":"..."}]

    可选参数 (有默认):
      version: 框架版本，默认 "2.0-SNAPSHOT"
      dependencies_version: SpringBoot 父依赖版本，默认 "3.2.5.RELEASE"
      output_path: 解压目标 (相对调用方 CWD)，默认 "workspace/backend"
      overwrite: 目标非空时是否覆盖，默认 False

    成功返回:
      {"status":"ok", "output_path", "files_created", "main_class",
       "build_command", "next_steps":[...]}

    失败返回:
      {"status":"error", "error_code", "message"}
      error_code 可能值:
        INVALID_PARAMS / TARGET_NOT_EMPTY / DOWNLOAD_FAILED /
        BACKEND_VALIDATION / ZIP_CORRUPTED
    """
    v = validate_params(package_name, component_id)
    if not v["valid"]:
        return {
            "status": "error",
            "error_code": "INVALID_PARAMS",
            "message": "; ".join(v["errors"])
        }

    target = Path(output_path).resolve()
    if target.exists() and any(target.iterdir()) and not overwrite:
        return {
            "status": "error",
            "error_code": "TARGET_NOT_EMPTY",
            "message": f"{output_path} 非空，传 overwrite=True 强制覆盖"
        }
    target.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": version,
        "packageName": package_name,
        "componentId": component_id,
        "serviceId": service_ids,
        "port": port,
        "errorCode": error_code,
        "dependenciesVersion": dependencies_version,
        "email": email,
        "author": author,
        "configInfo": middlewares,
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
            "message": f"HTTP {e.response.status_code}: {err_body}"
        }
    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error_code": "DOWNLOAD_FAILED",
            "message": str(e)
        }

    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            zf.extractall(target)
            files = zf.namelist()
    except zipfile.BadZipFile as e:
        return {
            "status": "error",
            "error_code": "ZIP_CORRUPTED",
            "message": str(e)
        }

    return {
        "status": "ok",
        "output_path": str(target),
        "files_created": len(files),
        "framework": "spring-boot",
        "framework_parent_version": dependencies_version,
        "main_class": f"{package_name}.Application",
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
