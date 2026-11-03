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

"""网关根地址和开发者中心页面链接按配置拼出来。"""

import pytest

from app_spark_api.infras.bk_paas import (
    BkPaaSConfigurationError,
    build_console_links,
    build_deployment_detail_url,
    build_gateway_base_url,
)


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
