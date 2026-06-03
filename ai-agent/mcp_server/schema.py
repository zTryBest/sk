# -*- coding: utf-8 -*-

from typing import Dict

from pydantic import BaseModel, Field


class ProductVersionQuery(BaseModel):
    product_id: str = Field(
        description="平台/产品标识，来自需求分析阶段确认的平台名称。"
    )
    product_version: str = Field(
        description="平台/产品版本，来自需求分析阶段确认的平台版本。"
    )
    component_overrides: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "临时组件版本覆盖，适合现场单独升级某组件的特殊情况。"
            "格式如 {'USER_CENTER': 'v1.3'}。"
        )
    )


class ComponentDocVersionQuery(BaseModel):
    component_id: str = Field(
        description="组件标识。"
    )


class ComponentDocResolveQuery(BaseModel):
    component_id: str = Field(
        description="组件标识。"
    )
    component_version: str = Field(
        description="实际组件版本，允许混合格式，如 v1.3、1.3.0、2024.06。"
    )


class ComponentDocMappingSubmit(ComponentDocResolveQuery):
    doc_version: str = Field(
        description="人工确认应使用的接口文档版本。"
    )
    reason: str = Field(
        default="",
        description="映射原因，例如“v1.3 无文档，研发确认沿用 v1.2”。"
    )
    created_by: str = Field(
        default="AI_AGENT",
        description="提交人或来源。"
    )


class RequirementApiQuery(ProductVersionQuery):
    requirement_item: str = Field(
        description="需求分析阶段产出的单个需求分解项。"
    )
    limit: int = Field(
        default=5,
        description="最多返回的候选 API 数量。"
    )


class ApiDetailQuery(BaseModel):
    component_id: str = Field(
        description="组件标识。"
    )
    component_version: str = Field(
        description="实际组件版本，用于解析接口文档版本和契约版本。"
    )
    method: str = Field(
        description="HTTP 方法，例如 GET、POST。"
    )
    api_path: str = Field(
        description="接口路径。"
    )
