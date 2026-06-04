# -*- coding: utf-8 -*-

import logging
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from fastmcp import FastMCP

from service.knowledge_service import KnowledgeService

from mcp_server.schema import (
    ApiDetailQuery,
    ComponentDocMappingSubmit,
    ComponentDocResolveQuery,
    ComponentSegmentQuery,
    ComponentDocVersionQuery,
    ProductVersionQuery,
    RequirementApiQuery,
)
from mcp_server.response import success, error


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

knowledge_service = KnowledgeService()

mcp = FastMCP(
    name="Enterprise-KnowledgeBase",
    auth=None
)


@mcp.tool(
    description="检查 MCP 服务是否正常运行。",
    timeout=10
)
def health_check():
    return success(
        knowledge_service.health_check()
    )


@mcp.tool(
    description="列出知识库中已维护的平台/产品版本。",
    timeout=10
)
def list_products():
    try:
        return success(
            knowledge_service.list_products()
        )
    except Exception as e:
        return error(str(e))


@mcp.tool(
    description=(
        "列出指定平台版本的默认组件清单，并可用 component_overrides 临时覆盖组件版本。"
        "用于方案设计阶段确认本次查询的组件版本范围。"
    ),
    timeout=15
)
def list_product_components(req: ProductVersionQuery):
    try:
        return success(
            knowledge_service.list_product_components(
                product_id=req.product_id,
                product_version=req.product_version,
                component_overrides=req.component_overrides
            )
        )
    except Exception as e:
        return error(str(e))


@mcp.tool(
    description="列出某个组件下面已经维护的组件段，例如 aaa-web、aaa-search。",
    timeout=15
)
def list_component_segments(req: ComponentSegmentQuery):
    try:
        return success(
            knowledge_service.list_component_segments(
                component_id=req.component_id
            )
        )
    except Exception as e:
        return error(str(e))


@mcp.tool(
    description=(
        "列出某个组件已经导入的接口文档版本。"
        "可传 segment_id 精确到组件段；不传则返回该组件所有段的文档版本。"
    ),
    timeout=15
)
def list_component_doc_versions(req: ComponentDocVersionQuery):
    try:
        return success(
            knowledge_service.list_component_doc_versions(
                component_id=req.component_id,
                segment_id=req.segment_id
            )
        )
    except Exception as e:
        return error(str(e))


@mcp.tool(
    description=(
        "解析某个实际组件版本应该使用哪个接口文档版本。"
        "支持版本格式混合；优先人工映射，其次同 major 最近低版本，再同 major 最近高版本。"
    ),
    timeout=15
)
def resolve_component_doc_version(req: ComponentDocResolveQuery):
    try:
        return success(
            knowledge_service.resolve_component_doc_version(
                component_id=req.component_id,
                segment_id=req.segment_id,
                component_version=req.component_version
            )
        )
    except Exception as e:
        return error(str(e))


@mcp.tool(
    description=(
        "提交组件实际版本到接口文档版本的人工映射。"
        "当自动解析不可靠或跨 major 版本需要人工确认时使用。"
    ),
    timeout=15
)
def submit_component_version_doc_mapping(req: ComponentDocMappingSubmit):
    try:
        return success(
            knowledge_service.submit_component_version_doc_mapping(
                component_id=req.component_id,
                segment_id=req.segment_id,
                component_version=req.component_version,
                doc_version=req.doc_version,
                reason=req.reason,
                created_by=req.created_by
            )
        )
    except Exception as e:
        return error(str(e))


@mcp.tool(
    description=(
        "核心工具：根据需求分解项，在指定平台版本和可选组件覆盖范围内查找候选 API。"
        "先检索 api_identity，再解析组件文档版本和 api_contract，返回版本依据和风险。"
    ),
    timeout=45
)
def find_apis_for_requirement(req: RequirementApiQuery):
    try:
        return success(
            knowledge_service.find_apis_for_requirement(
                product_id=req.product_id,
                product_version=req.product_version,
                requirement_item=req.requirement_item,
                component_overrides=req.component_overrides,
                limit=req.limit
            )
        )
    except Exception as e:
        return error(str(e))


@mcp.tool(
    description=(
        "查询稳定 API 身份在某个实际组件版本下应使用的接口契约。"
        "返回 api_identity、api_contract、resolved_doc_version、match_level、risk。"
    ),
    timeout=20
)
def get_api_detail(req: ApiDetailQuery):
    try:
        return success(
            knowledge_service.get_api_detail(
                component_id=req.component_id,
                segment_id=req.segment_id,
                component_version=req.component_version,
                method=req.method,
                api_path=req.api_path
            )
        )
    except Exception as e:
        return error(str(e))


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp")

    if transport == "stdio":
        logger.info("Starting MCP server with stdio transport")
        mcp.run(transport="stdio")
    else:
        logger.info(
            "Starting MCP server with %s transport at http://%s:%s%s",
            transport,
            host,
            port,
            path,
        )
        mcp.run(
            transport=transport,
            host=host,
            port=port,
            path=path,
        )
