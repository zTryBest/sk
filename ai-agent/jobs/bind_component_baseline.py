# -*- coding: utf-8 -*-

import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.design_phase import (  # noqa: E402
    ComponentCatalog,
    ProductComponentBaseline,
)
from repository.design_repository import DesignRepository  # noqa: E402
from utils.identifier_utils import normalize_identifier  # noqa: E402


def bind_component_baseline(
        product_id: str,
        product_version: str,
        component_id: str,
        component_version: str,
        product_name: str = "",
        product_description: str = "",
        component_name: str = "",
        component_description: str = "",
        component_scene: str = "",
        source: str = "BASELINE"
):
    product_id = normalize_identifier(product_id)
    component_id = normalize_identifier(component_id)

    repo = DesignRepository()
    product_release_id = repo.upsert_product_release(
        product_id=product_id,
        product_version=product_version,
        product_name=product_name,
        description=product_description
    )

    if component_name or component_description or component_scene:
        repo.upsert_component(
            ComponentCatalog(
                component_id=component_id,
                component_name=component_name or component_id,
                description=component_description,
                scene=component_scene
            )
        )

    baseline_id = repo.upsert_product_component_baseline(
        ProductComponentBaseline(
            product_id=product_id,
            product_version=product_version,
            component_id=component_id,
            component_version=component_version,
            source=source
        )
    )

    return {
        "product_release_id": product_release_id,
        "baseline_id": baseline_id,
        "product_id": product_id,
        "product_version": product_version,
        "component_id": component_id,
        "component_version": component_version
    }


def main():
    parser = argparse.ArgumentParser(
        description="Bind an imported component to a product baseline."
    )
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--product-version", required=True)
    parser.add_argument("--component-id", required=True)
    parser.add_argument("--component-version", required=True)
    parser.add_argument("--product-name", default="")
    parser.add_argument("--product-description", default="")
    parser.add_argument("--component-name", default="")
    parser.add_argument("--component-description", default="")
    parser.add_argument("--component-scene", default="")
    parser.add_argument("--source", default="BASELINE")

    args = parser.parse_args()
    result = bind_component_baseline(
        product_id=args.product_id,
        product_version=args.product_version,
        component_id=args.component_id,
        component_version=args.component_version,
        product_name=args.product_name,
        product_description=args.product_description,
        component_name=args.component_name,
        component_description=args.component_description,
        component_scene=args.component_scene,
        source=args.source
    )
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
