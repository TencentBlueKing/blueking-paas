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

from paas_wl.cnative.specs.constants import LEGACY_PROC_RES_ANNO_KEY, ApiVersion, ResQuotaPlan
from paas_wl.cnative.specs.models import create_app_resource
from paas_wl.cnative.specs.procs.quota import ResourceQuota, ResourceQuotaReader

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestResourceQuotaReader:
    def test_v1alpha1(self, bk_stag_wl_app):
        res = create_app_resource(bk_stag_wl_app.name, 'busybox')
        res.apiVersion = ApiVersion.V1ALPHA1
        res.spec.processes[0].cpu = "200m"
        res.spec.processes[0].memory = "128Mi"
        assert ResourceQuotaReader(res).read_all() == {'web': ResourceQuota(cpu="200m", memory="128Mi")}

    def test_v1alpha2_legacy(self, bk_stag_wl_app):
        res = create_app_resource(bk_stag_wl_app.name, 'busybox')
        res.apiVersion = ApiVersion.V1ALPHA2
        res.metadata.annotations[LEGACY_PROC_RES_ANNO_KEY] = '{"web": {"cpu": "300m", "memory": "512Mi"}}'
        assert ResourceQuotaReader(res).read_all() == {"web": ResourceQuota(cpu="300m", memory="512Mi")}

    def test_v1alpha2_quota_plan(self, bk_stag_wl_app):
        res = create_app_resource(bk_stag_wl_app.name, 'busybox')
        res.apiVersion = ApiVersion.V1ALPHA2
        res.spec.processes[0].resQuotaPlan = ResQuotaPlan.P_2C2G
        assert ResourceQuotaReader(res).read_all() == {"web": ResourceQuota(cpu="2000m", memory="2048Mi")}
