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

import json

import pytest
from django_dynamic_fixture import G

from paasng.accessories.services.models import Plan, PreCreatedInstance

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True, params=[{"recyclable": True}, {}])
def bk_plan(request, bk_service):
    return G(Plan, config=json.dumps(request.param), service=bk_service)


class TestResourcePoolProvider:
    @pytest.fixture(params=[1, 3])
    def pools(self, request, bk_plan):
        result = []
        for i in range(request.param):
            result.append(G(PreCreatedInstance, plan=bk_plan, credentials=json.dumps({"idx": i})))
        return result

    def test_provision(self, bk_service, bk_plan, pools):
        instance = bk_service.create_service_instance_by_plan(bk_plan, {})
        assert json.loads(instance.credentials)["REDIS_IDX"] == json.loads(pools[0].credentials)["idx"]
        expect = PreCreatedInstance.objects.get(pk=pools[0].pk)
        assert instance.config.pop("__pk__") == str(expect.pk)
        assert instance.config == {
            "enable_tls": False,
            "is_pre_created": True,
            "provider_name": "redis",
            "recyclable": False,
        }
        assert expect.is_allocated

    def test_delete(self, bk_service, bk_plan, pools):
        instance = bk_service.create_service_instance_by_plan(bk_plan, {})
        assert PreCreatedInstance.objects.get(pk=pools[0].pk).is_allocated
        bk_service.delete_service_instance(instance)
        if json.loads(bk_plan.config).get("recyclable", False):
            assert not PreCreatedInstance.objects.get(pk=pools[0].pk).is_allocated
            assert PreCreatedInstance.objects.count() == len(pools)
        else:
            assert PreCreatedInstance.objects.get(pk=pools[0].pk).is_allocated
            assert PreCreatedInstance.objects.count() == len(pools)
