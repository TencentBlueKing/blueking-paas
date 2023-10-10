# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import json
from unittest import mock

import pytest

from paas_wl.bk_app.cnative.specs.addons import inject_to_app_resource
from paas_wl.bk_app.cnative.specs.constants import BKPAAS_ADDONS_ANNO_KEY
from paas_wl.bk_app.cnative.specs.crd.bk_app import ApiVersion, BkAppAddon, BkAppAddonSpec, BkAppResource

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


@pytest.fixture()
def mock_service_mgr(request):
    def fake_list_binded(module):
        return [type("", (), dict(name=name)) for name in request.param]

    with mock.patch("paas_wl.bk_app.cnative.specs.addons.mixed_service_mgr.list_binded") as list_binded:
        list_binded.side_effect = fake_list_binded
        yield request.param


@pytest.mark.parametrize(
    "mock_service_mgr, manifest, expected_addons",
    [
        (
            ["mysql", "rabbitmq"],
            BkAppResource(
                apiVersion=ApiVersion.V1ALPHA1,
                metadata={"name": "foo"},
                spec={},
            ),
            [],
        ),
        (
            ["mysql", "rabbitmq"],
            BkAppResource(
                apiVersion=ApiVersion.V1ALPHA2,
                metadata={"name": "foo"},
                spec={},
            ),
            [BkAppAddon(name='mysql', specs=[]), BkAppAddon(name='rabbitmq', specs=[])],
        ),
        (
            ["mysql", "rabbitmq"],
            BkAppResource(
                apiVersion=ApiVersion.V1ALPHA2,
                metadata={"name": "foo"},
                spec={"addons": [{"name": "redis"}]},
            ),
            [
                BkAppAddon(name='redis', specs=[]),
                BkAppAddon(name='mysql', specs=[]),
                BkAppAddon(name='rabbitmq', specs=[]),
            ],
        ),
        (
            ["mysql", "rabbitmq"],
            BkAppResource(
                apiVersion=ApiVersion.V1ALPHA2,
                metadata={"name": "foo"},
                spec={"addons": [{"name": "mysql"}]},
            ),
            [
                BkAppAddon(name='mysql', specs=[]),
                BkAppAddon(name='rabbitmq', specs=[]),
            ],
        ),
        (
            ["mysql", "rabbitmq"],
            BkAppResource(
                apiVersion=ApiVersion.V1ALPHA2,
                metadata={"name": "foo"},
                spec={"addons": [{"name": "mysql", "specs": [{"name": "version", "value": "5.7"}]}]},
            ),
            [
                BkAppAddon(name='mysql', specs=[BkAppAddonSpec(name='version', value='5.7')]),
                BkAppAddon(name='rabbitmq', specs=[]),
            ],
        ),
    ],
    indirect=["mock_service_mgr"],
)
def test_inject_to_app_resource(bk_stag_env, mock_service_mgr, manifest: BkAppResource, expected_addons):
    inject_to_app_resource(bk_stag_env, manifest)

    assert manifest.metadata.annotations[BKPAAS_ADDONS_ANNO_KEY] == json.dumps(mock_service_mgr)
    assert manifest.spec.addons == expected_addons
