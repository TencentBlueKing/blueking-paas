# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

from unittest.mock import PropertyMock, patch

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paasng.accessories.publish.market.models import Product
from paasng.accessories.publish.market.protections import AppPublishPreparer
from paasng.accessories.publish.market.status import publish_to_market_by_deployment
from paasng.platform.applications.models import Application
from paasng.platform.engine.models import Deployment
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.source_types import get_sourcectl_names
from tests.conftest import mark_skip_if_console_not_configured
from tests.utils.helpers import generate_random_string

pytestmark = [
    mark_skip_if_console_not_configured(),
    pytest.mark.django_db(databases=["default", "workloads"]),
]


@pytest.mark.usefixtures("_init_tmpls")
@pytest.mark.parametrize(
    (
        "confirm_required_when_publish",
        "deployment_status",
        "auto_enable_when_deploy",
        "released_state",
        "console_state",
    ),
    [
        (False, "failed", True, False, False),
        (False, "pending", True, False, False),
        (True, "successful", False, False, False),
        (False, "successful", True, True, True),
    ],
)
def test_create_then_release(
    api_client,
    mock_wl_services_in_creation,
    mock_paas_analysis_client,
    mock_initialize_vcs_with_template,
    confirm_required_when_publish,
    auto_enable_when_deploy,
    deployment_status,
    released_state,
    console_state,
):
    # mock spec when creating application
    with patch(
        "paasng.platform.applications.specs.AppSpecs.confirm_required_when_publish",
        new_callable=PropertyMock,
        return_value=confirm_required_when_publish,
    ):
        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            "/api/bkapps/applications/v2/",
            data={
                "region": settings.DEFAULT_REGION_NAME,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "engine_enabled": True,
                "engine_params": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS.value,
                    "source_control_type": get_sourcectl_names().bk_svn,
                    "source_init_template": "dummy_template",
                },
                "market_params": {"enabled": False, "source_url_type": 1},
            },
        )

    assert (
        response.status_code == 201
    ), f"status code invalid: {response.status_code}, response content: {response.data}"
    pk = response.json()["application"]["id"]
    application = Application.objects.get(pk=pk)

    market_config = application.market_config
    assert market_config.auto_enable_when_deploy == auto_enable_when_deploy
    assert not market_config.enabled

    # 创建产品信息
    G(Product, application=application, type=1)

    # 模拟由部署触发发布流程
    deployment = G(
        Deployment,
        app_environment=application.get_default_module().get_envs("prod"),
        status=deployment_status,
    )
    publish_to_market_by_deployment(deployment)

    market_config.refresh_from_db()
    assert market_config.enabled == released_state

    # 通过 mock 控制 Preparer 所依赖的“环境部署状态”，保持与部署结果同步
    with patch("paasng.accessories.publish.market.protections.env_is_deployed", return_value=deployment_status):
        assert (market_config.enabled and AppPublishPreparer(application).all_matched) == console_state

    if console_state:
        assert not market_config.auto_enable_when_deploy
