# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""校验网关 definition.yaml 中声明的 MCP Server 所引用的资源均已正确声明参数"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest
import yaml
from django.conf import settings

APIGW_DIR = Path(settings.BASE_DIR) / "support-files" / "apigw"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")


def _load_mcp_resource_names() -> List[Tuple[str, str]]:
    definition = yaml.safe_load((APIGW_DIR / "definition.yaml").read_text(encoding="utf-8"))
    return [
        (mcp["name"], name)
        for stage in definition.get("stages", [])
        for mcp in stage.get("mcp_servers", [])
        for name in mcp["resource_names"]
    ]


def _load_resources() -> Dict[str, Tuple[str, dict]]:
    resources = yaml.safe_load((APIGW_DIR / "resources.yaml").read_text(encoding="utf-8"))
    return {
        op["operationId"]: (path, op)
        for path, methods in resources["paths"].items()
        for method, op in methods.items()
        if method in HTTP_METHODS
    }


def _placeholders(path: str) -> Set[str]:
    return {name for name in PLACEHOLDER_RE.findall(path) if not name.startswith("env.")}


MCP_RESOURCE_NAMES = _load_mcp_resource_names()
RESOURCES = _load_resources()


def test_mcp_servers_declared():
    assert MCP_RESOURCE_NAMES, "no mcp server declared in definition.yaml"


@pytest.mark.parametrize(("mcp_name", "resource_name"), MCP_RESOURCE_NAMES)
def test_mcp_resource_schema(mcp_name, resource_name):
    assert resource_name in RESOURCES, f"[{mcp_name}] resource {resource_name} not found"

    path, op = RESOURCES[resource_name]
    gw_conf = op["x-bk-apigateway-resource"]
    # MCP 要求资源参数已确认：要么声明了参数/请求体，要么通过 noneSchema 标记"已确认无参数"
    has_schema = bool(op.get("parameters") or op.get("requestBody"))
    assert has_schema or gw_conf.get("noneSchema"), f"{resource_name} has no schema declared"
    if gw_conf.get("noneSchema"):
        assert not _placeholders(path), f"{resource_name} has path params but marked as noneSchema"

    declared = {p["name"] for p in op.get("parameters", []) if p["in"] == "path"}
    assert declared == _placeholders(path), f"{resource_name}: path params mismatch with {path}"
    assert declared == _placeholders(gw_conf["backend"]["path"]), f"{resource_name}: backend path params mismatch"
