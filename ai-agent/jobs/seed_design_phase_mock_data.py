# -*- coding: utf-8 -*-

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.design_phase import (  # noqa: E402
    ApiContract,
    ApiIdentity,
    ComponentCatalog,
    ComponentDocVersion,
    ProductComponentBaseline,
)
from repository.design_repository import DesignRepository  # noqa: E402


def seed():
    repo = DesignRepository()

    repo.upsert_product_release(
        product_id="SIM_PLATFORM_V2",
        product_version="5.0",
        product_name="模拟定制平台",
        description="用于验证接口身份去重、契约版本解析和组件版本覆盖。"
    )

    repo.upsert_component(
        ComponentCatalog(
            component_id="USER_CENTER",
            component_name="用户中心组件",
            description="提供用户资料查询、用户状态、组织归属、联系人信息等基础用户能力。",
            scene="当定制需求涉及查询用户详情、展示用户基础信息、校验用户状态时使用。"
        )
    )

    repo.upsert_component(
        ComponentCatalog(
            component_id="ORDER_CENTER",
            component_name="订单中心组件",
            description="提供订单查询、订单详情、订单状态流转等能力。",
            scene="当定制需求涉及订单列表、订单详情、订单状态判断时使用。"
        )
    )

    repo.upsert_product_component_baseline(
        ProductComponentBaseline(
            product_id="SIM_PLATFORM_V2",
            product_version="5.0",
            component_id="USER_CENTER",
            component_version="v1.3",
            source="BASELINE"
        )
    )

    repo.upsert_product_component_baseline(
        ProductComponentBaseline(
            product_id="SIM_PLATFORM_V2",
            product_version="5.0",
            component_id="ORDER_CENTER",
            component_version="v2.1",
            source="BASELINE"
        )
    )

    for doc_version in ["v1.0", "v1.2", "v2.1"]:
        repo.upsert_component_doc_version(
            ComponentDocVersion(
                component_id="USER_CENTER",
                doc_version=doc_version,
                doc_url=f"https://intranet-docs.example/user-center/{doc_version}/swagger.json",
                crawl_status="SUCCESS"
            )
        )

    repo.upsert_component_doc_version(
        ComponentDocVersion(
            component_id="ORDER_CENTER",
            doc_version="v2.1",
            doc_url="https://intranet-docs.example/order-center/v2.1/swagger.json",
            crawl_status="SUCCESS"
        )
    )

    user_api_id = repo.upsert_api_identity(
        ApiIdentity(
            component_id="USER_CENTER",
            method="GET",
            api_path="/api/users/{userId}",
            api_name="查询用户详情",
            capability_tags=["用户查询", "用户详情", "基础资料"],
            scene="根据用户ID查询用户基础资料。",
            description="用于定制页面展示用户姓名、状态、部门等信息。"
        )
    )

    repo.upsert_api_contract(
        ApiContract(
            api_identity_id=user_api_id,
            doc_version="v1.0",
            params_desc="userId: 用户唯一标识。",
            request_schema={"path": {"userId": "string"}},
            response_schema={
                "userId": "string",
                "name": "string",
                "status": "string"
            },
            response_demo='{"userId":"U10001","name":"张三","status":"ACTIVE"}',
            usage_notes="自动编码时需要将路径参数 userId 替换为真实用户ID。",
            source_url="https://intranet-docs.example/user-center/v1.0/swagger.json"
        )
    )
    repo.upsert_api_lifecycle(
        api_identity_id=user_api_id,
        doc_version="v1.0",
        status="PRESENT",
        change_type="ADDED"
    )

    repo.upsert_api_contract(
        ApiContract(
            api_identity_id=user_api_id,
            doc_version="v1.2",
            params_desc="userId: 用户唯一标识。",
            request_schema={"path": {"userId": "string"}},
            response_schema={
                "userId": "string",
                "name": "string",
                "status": "string",
                "department": "string"
            },
            response_demo='{"userId":"U10001","name":"张三","status":"ACTIVE","department":"研发部"}',
            usage_notes="v1.2 起响应增加 department 字段。",
            source_url="https://intranet-docs.example/user-center/v1.2/swagger.json"
        )
    )
    repo.upsert_api_lifecycle(
        api_identity_id=user_api_id,
        doc_version="v1.2",
        status="PRESENT",
        change_type="CHANGED"
    )

    repo.upsert_api_contract(
        ApiContract(
            api_identity_id=user_api_id,
            doc_version="v2.1",
            params_desc="userId: 用户唯一标识；includeRoles: 是否返回角色。",
            request_schema={
                "path": {"userId": "string"},
                "query": {"includeRoles": "boolean"}
            },
            response_schema={
                "userId": "string",
                "name": "string",
                "status": "string",
                "department": "string",
                "roles": "array"
            },
            response_demo='{"userId":"U10001","name":"张三","status":"ACTIVE","department":"研发部","roles":["admin"]}',
            usage_notes="v2.1 支持 includeRoles 查询角色信息。",
            source_url="https://intranet-docs.example/user-center/v2.1/swagger.json"
        )
    )
    repo.upsert_api_lifecycle(
        api_identity_id=user_api_id,
        doc_version="v2.1",
        status="PRESENT",
        change_type="CHANGED"
    )

    order_api_id = repo.upsert_api_identity(
        ApiIdentity(
            component_id="ORDER_CENTER",
            method="GET",
            api_path="/api/orders/{orderId}",
            api_name="查询订单详情",
            capability_tags=["订单查询", "订单详情"],
            scene="根据订单ID查询订单详情。",
            description="用于定制页面展示订单状态、金额等信息。"
        )
    )

    repo.upsert_api_contract(
        ApiContract(
            api_identity_id=order_api_id,
            doc_version="v2.1",
            params_desc="orderId: 订单唯一标识。",
            request_schema={"path": {"orderId": "string"}},
            response_schema={
                "orderId": "string",
                "status": "string",
                "amount": "number"
            },
            response_demo='{"orderId":"O90001","status":"PAID","amount":128.5}',
            usage_notes="自动编码时需要将路径参数 orderId 替换为真实订单ID。",
            source_url="https://intranet-docs.example/order-center/v2.1/swagger.json"
        )
    )
    repo.upsert_api_lifecycle(
        api_identity_id=order_api_id,
        doc_version="v2.1",
        status="PRESENT",
        change_type="ADDED"
    )

    print("seeded SIM_PLATFORM_V2 mock data")


if __name__ == "__main__":
    seed()
