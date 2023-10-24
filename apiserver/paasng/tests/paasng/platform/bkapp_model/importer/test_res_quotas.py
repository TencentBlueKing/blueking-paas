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
import pytest
from django_dynamic_fixture import G

from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import ResQuotaOverlay
from paasng.platform.bkapp_model.importer.res_quotas import import_res_quota_overlay
from paasng.platform.bkapp_model.models import ProcessSpecEnvOverlay

pytestmark = pytest.mark.django_db


class Test__import_res_quota_overlay:
    def test_integrated(self, bk_module, proc_web, proc_celery):
        G(
            ProcessSpecEnvOverlay,
            proc_spec=proc_web,
            environment_name="stag",
            plan_name=ResQuotaPlan.P_DEFAULT,
        )
        G(
            ProcessSpecEnvOverlay,
            proc_spec=proc_celery,
            environment_name="prod",
            plan_name=ResQuotaPlan.P_2C2G,
        )
        assert ProcessSpecEnvOverlay.objects.count() == 2

        ret = import_res_quota_overlay(
            bk_module,
            [
                ResQuotaOverlay(envName="prod", process="web", plan=ResQuotaPlan.P_4C4G),
                ResQuotaOverlay(envName="prod", process="web", plan=ResQuotaPlan.P_4C4G),
            ],
        )
        assert ProcessSpecEnvOverlay.objects.count() == 3
        assert ret.updated_num == 1
        assert ret.created_num == 1
        assert ret.deleted_num == 1
