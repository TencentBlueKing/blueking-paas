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

import pytest

from paas_wl.workloads.networking.ingress.models import AppDomain, Domain
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.models import Module
from tests.paas_wl.utils.release import create_release
from tests.utils.helpers import (
    generate_random_string,
    initialize_module,
)

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def create_module(bk_app):
    module = Module.objects.create(region=bk_app.region, application=bk_app, name=generate_random_string(length=8))
    initialize_module(module)
    return module


class TestAppEntranceViewSet:
    def test_list_all_entrances(self, bk_user, api_client, bk_app, bk_module, bk_stag_env, bk_stag_wl_app):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.save()
        url = f"/api/bkapps/applications/{bk_app.code}/entrances/"
        resp = api_client.get(url)
        # 未部署, 仅独立域名
        assert resp.json() == [
            {
                "name": "default",
                "is_default": True,
                "envs": {
                    "stag": [
                        {
                            "module": "default",
                            "env": "stag",
                            "address": {
                                "id": None,
                                "url": f"http://stag-dot-{bk_app.code}.example.com",
                                "type": "subdomain",
                            },
                            "is_running": False,
                        }
                    ],
                    "prod": [
                        {
                            "module": "default",
                            "env": "prod",
                            "address": {"id": None, "url": f"http://{bk_app.code}.example.com", "type": "subdomain"},
                            "is_running": False,
                        }
                    ],
                },
            }
        ]

        # 添加独立域名
        # source type: custom
        custom_domain = Domain.objects.create(
            name="foo-custom.example.com",
            path_prefix="/subpath/",
            module_id=bk_module.id,
            environment_id=bk_stag_env.id,
        )

        resp = api_client.get(url)
        assert resp.json() == [
            {
                "name": "default",
                "is_default": True,
                "envs": {
                    "stag": [
                        {
                            "module": "default",
                            "env": "stag",
                            "address": {
                                "id": None,
                                "url": f"http://stag-dot-{bk_app.code}.example.com",
                                "type": "subdomain",
                            },
                            "is_running": False,
                        },
                        {
                            "module": "default",
                            "env": "stag",
                            "address": {
                                "id": custom_domain.id,
                                "url": "http://foo-custom.example.com/subpath/",
                                "type": "custom",
                            },
                            "is_running": False,
                        },
                    ],
                    "prod": [
                        {
                            "module": "default",
                            "env": "prod",
                            "address": {"id": None, "url": f"http://{bk_app.code}.example.com", "type": "subdomain"},
                            "is_running": False,
                        }
                    ],
                },
            }
        ]

        # test field `is_running`
        create_release(bk_stag_wl_app, bk_user, failed=False)
        AppDomain.objects.create(app=bk_stag_wl_app, host=f"stag-dot-{bk_app.code}.example.com", source=2)
        resp = api_client.get(url)
        assert resp.json() == [
            {
                "name": "default",
                "is_default": True,
                "envs": {
                    "stag": [
                        {
                            "module": "default",
                            "env": "stag",
                            "address": {
                                "id": None,
                                "url": f"http://stag-dot-{bk_app.code}.example.com/",
                                "type": "subdomain",
                            },
                            "is_running": True,
                        },
                        {
                            "module": "default",
                            "env": "stag",
                            "address": {
                                "id": custom_domain.id,
                                "url": "http://foo-custom.example.com/subpath/",
                                "type": "custom",
                            },
                            "is_running": True,
                        },
                    ],
                    "prod": [
                        {
                            "module": "default",
                            "env": "prod",
                            "address": {"id": None, "url": f"http://{bk_app.code}.example.com", "type": "subdomain"},
                            "is_running": False,
                        }
                    ],
                },
            }
        ]
