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

from paasng.platform.bkapp_model.importer.serializers import BkAppSpecInputSLZ
from paasng.platform.bkapp_model.importer.svc_discovery import import_svc_discovery
from paasng.platform.bkapp_model.models import SvcDiscConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class Test__import_svc_discoverys:
    def test_integrated(self, bk_module):
        manifest = {
            "spec": {
                "svcDiscovery": {
                    "bkSaaS": [
                        {"bkAppCode": "bk-iam"},
                        {"bkAppCode": "bk-sops", "moduleName": "bk-backend"},
                    ],
                },
                "processes": [],
            }
        }
        spec_slz = BkAppSpecInputSLZ(data=manifest["spec"])
        spec_slz.is_valid(raise_exception=True)
        validated_data = spec_slz.validated_data

        ret = import_svc_discovery(
            bk_module,
            validated_data["svcDiscovery"],
        )

        svc_disc = SvcDiscConfig.objects.get(application=bk_module.application)

        assert len(svc_disc.bk_saas) == 2
        assert ret.created_num == 1

        manifest["spec"]["svcDiscovery"]["bkSaaS"] = [  # type: ignore
            {"bkAppCode": "bk-iam"},
            {"bkAppCode": "bk-sops", "moduleName": "bk-frontend"},
        ]

        spec_slz = BkAppSpecInputSLZ(data=manifest["spec"])
        spec_slz.is_valid(raise_exception=True)
        validated_data = spec_slz.validated_data

        ret = import_svc_discovery(
            bk_module,
            validated_data["svcDiscovery"],
        )

        svc_disc = SvcDiscConfig.objects.get(application=bk_module.application)
        assert len(svc_disc.bk_saas) == 3
        assert ret.updated_num == 1
