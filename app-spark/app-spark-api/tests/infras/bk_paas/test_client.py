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

"""网关根地址和开发者中心页面链接按配置拼出来；校验应用 ID 和名称的结果按字段读出来。"""

import json

import httpx2
import pytest

from app_spark_api.infras.bk_paas import (
    AppFieldError,
    AppFieldProblem,
    BkPaaSClient,
    BkPaaSConfigurationError,
    BkPaaSUnavailableError,
    build_console_links,
    build_deployment_detail_url,
    build_gateway_base_url,
)

BASE_URL = "https://bkapi.example.com/api/bkpaas3/prod"


def make_client(answer, requests: list[httpx2.Request]) -> BkPaaSClient:
    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return answer

    return BkPaaSClient(BASE_URL, "bk-app-spark", "secret", transport=httpx2.MockTransport(handle))


async def test_validating_sends_the_tenant_and_reads_each_field():
    requests: list[httpx2.Request] = []
    answer = httpx2.Response(
        200,
        json={
            "is_valid": False,
            "fields_detail": {
                "name": [{"code": "unique", "message": "名称已存在"}],
                "code": [{"code": "max_length", "message": "太长了"}],
            },
        },
    )

    async with make_client(answer, requests) as client:
        result = await client.validate_app_basic_info(
            "Spark", code="spark-demo", app_tenant_mode="single", app_tenant_id="t1"
        )

    assert requests[0].url.path == "/api/bkpaas3/prod/system/bkapps/applications/validations/"
    assert json.loads(requests[0].content) == {
        "name": "Spark",
        "code": "spark-demo",
        "app_tenant_mode": "single",
        "app_tenant_id": "t1",
    }
    assert result.name_error == AppFieldError(AppFieldProblem.TAKEN, "名称已存在")
    assert result.code_error == AppFieldError(AppFieldProblem.INVALID, "太长了")


async def test_validating_only_the_name_leaves_out_the_code():
    requests: list[httpx2.Request] = []
    answer = httpx2.Response(200, json={"is_valid": True, "fields_detail": {}})

    async with make_client(answer, requests) as client:
        result = await client.validate_app_basic_info("Spark")

    assert json.loads(requests[0].content) == {"name": "Spark"}
    assert (result.code_error, result.name_error) == (None, None)


async def test_an_unreadable_validation_answer_counts_as_unavailable():
    async with make_client(httpx2.Response(200, json={"is_valid": False}), []) as client:
        with pytest.raises(BkPaaSUnavailableError):
            await client.validate_app_basic_info("Spark")


@pytest.mark.parametrize(
    ("tmpl", "expected"),
    [
        ("https://bkapi.example.com/api/{api_name}/", "https://bkapi.example.com/api/paasv3/stag"),
        ("https://{api_name}.apigw.example.com", "https://paasv3.apigw.example.com/stag"),
    ],
)
def test_gateway_base_url_uses_the_configured_gateway_name(settings, tmpl, expected):
    settings.BK_API_URL_TMPL = tmpl
    settings.BKPAAS_APIGW_ENVIRONMENT = "stag"
    settings.BKPAAS_APIGW_NAME = "paasv3"

    assert build_gateway_base_url() == expected


@pytest.mark.parametrize(
    "tmpl", ["", "https://bkapi.example.com/api/bkpaas3/", "https://{api_name}.{zone}.example.com"]
)
def test_gateway_base_url_refuses_an_unusable_template(settings, tmpl):
    settings.BK_API_URL_TMPL = tmpl

    with pytest.raises(BkPaaSConfigurationError):
        build_gateway_base_url()


def test_console_links_point_at_the_cloud_native_pages():
    app = "https://bkpaas.example.com/developer-center/apps/demo-a1b2"

    links = build_console_links("https://bkpaas.example.com/", "demo-a1b2", "default")

    assert links is not None
    assert (links.logs, links.deployments, links.env_vars, links.members) == (
        f"{app}/default/logging",
        f"{app}/deployments/prod",
        f"{app}/default/settings/modules/env",
        f"{app}/settings/application/member",
    )
    assert build_deployment_detail_url("https://bkpaas.example.com", "demo-a1b2", "d-1") == (
        f"{app}/deployments/history?logId=d-1"
    )
    assert build_console_links("", "demo-a1b2", "default") is None
