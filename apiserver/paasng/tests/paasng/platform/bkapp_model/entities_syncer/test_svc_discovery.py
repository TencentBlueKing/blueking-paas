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
from django_dynamic_fixture import G

from paasng.platform.bkapp_model.entities import SvcDiscConfig, SvcDiscEntryBkSaaS
from paasng.platform.bkapp_model.entities_syncer import sync_svc_discovery
from paasng.platform.bkapp_model.models import SvcDiscConfig as SvcDiscConfigDB

pytestmark = pytest.mark.django_db


class Test__sync_svc_discoverys:
    def test_create(self, bk_module):
        ret = sync_svc_discovery(
            bk_module,
            SvcDiscConfig(bk_saas=[SvcDiscEntryBkSaaS(bk_app_code="bk-iam", module_name="api")]),
        )

        svc_disc = SvcDiscConfigDB.objects.get(application=bk_module.application)

        assert svc_disc.bk_saas == [SvcDiscEntryBkSaaS(bk_app_code="bk-iam", module_name="api")]
        assert ret.created_num == 1

    def test_update(self, bk_module):
        G(SvcDiscConfigDB, application=bk_module.application, bk_saas=[SvcDiscEntryBkSaaS(bk_app_code="bk-iam")])

        ret = sync_svc_discovery(
            bk_module,
            SvcDiscConfig(
                bk_saas=[
                    SvcDiscEntryBkSaaS(bk_app_code="bk-iam"),
                    SvcDiscEntryBkSaaS(bk_app_code="bk-iam", module_name="api2"),
                    SvcDiscEntryBkSaaS(bk_app_code="bk-iam", module_name="api3"),
                ]
            ),
        )

        assert len(SvcDiscConfigDB.objects.get(application=bk_module.application).bk_saas) == 3

        assert ret.created_num == 0
        assert ret.updated_num == 1
        assert ret.deleted_num == 0

    def test_delete(self, bk_module):
        G(SvcDiscConfigDB, application=bk_module.application, bk_saas=[SvcDiscEntryBkSaaS(bk_app_code="bk-iam")])

        ret = sync_svc_discovery(bk_module, SvcDiscConfig(bk_saas=[]))

        assert ret.deleted_num == 1
        assert SvcDiscConfigDB.objects.filter(application=bk_module.application).exists() is False
