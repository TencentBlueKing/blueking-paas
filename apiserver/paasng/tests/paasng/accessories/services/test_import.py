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
from textwrap import dedent

import pytest
import yaml
from django_dynamic_fixture import G

from paasng.accessories.services.models import Plan, PreCreatedInstance
from paasng.accessories.services.serializers import PreCreatedInstanceImportSLZ
from paasng.core.tenant.user import DEFAULT_TENANT_ID

pytestmark = pytest.mark.django_db

DUMMY_CREDENTIALS = dedent(
    """
  {
    "host": "10000",
    "port": 10086,
    "password": "********"
  }
    """
)


class TestPreCreatedInstanceImport:
    @pytest.mark.parametrize(
        "input_",
        [
            {"plan": "plan-b", "config": {}, "credentials": DUMMY_CREDENTIALS},
            {"plan": "plan-b", "config": {"a": "b"}, "credentials": DUMMY_CREDENTIALS},
        ],
    )
    def test_import_single(self, bk_service, bk_plan, input_):
        assert PreCreatedInstance.objects.filter(plan=bk_plan).count() == 0
        slz = PreCreatedInstanceImportSLZ(data=input_, context={"service": bk_service, "tenant_id": DEFAULT_TENANT_ID})
        slz.is_valid(raise_exception=True)
        slz.save()

        assert PreCreatedInstance.objects.filter(plan=bk_plan).count() == 1
        instance = PreCreatedInstance.objects.get(plan=bk_plan)
        assert instance.config == input_["config"]
        assert json.loads(instance.credentials) == json.loads(DUMMY_CREDENTIALS)

    @pytest.mark.parametrize(
        ("input_", "expected"),
        [
            ([], 0),
            ([{"plan": "plan-b", "config": {}, "credentials": DUMMY_CREDENTIALS}], 1),
            (
                [
                    {"plan": "plan-b", "config": {}, "credentials": DUMMY_CREDENTIALS},
                    {"plan": "plan-b", "config": {}, "credentials": DUMMY_CREDENTIALS},
                ],
                2,
            ),
        ],
    )
    def test_import_multi(self, bk_service, bk_plan, input_, expected):
        assert PreCreatedInstance.objects.filter(plan=bk_plan).count() == 0
        slz = PreCreatedInstanceImportSLZ(
            data=input_, context={"service": bk_service, "tenant_id": DEFAULT_TENANT_ID}, many=True
        )
        slz.is_valid(raise_exception=True)
        slz.save()
        assert PreCreatedInstance.objects.filter(plan=bk_plan).count() == expected

    @pytest.mark.parametrize(
        ("input_", "expected"),
        [
            (
                dedent(
                    """
        plan: plan-b
        config: "{}"
        credentials: |
            {
            "host": "10000",
            "port": 10086,
            "password": "********"
            }"""
                ),
                1,
            ),
            (
                dedent(
                    """
        plan: plan-b
        config: "{}"
        credentials: |
            {
            "host": "10000",
            "port": 10086,
            "password": "********"
            }
        ---
        plan: plan-b
        config: "{}"
        credentials: |
            {
            "host": "10000",
            "port": 10086,
            "password": "********"
            }"""
                ),
                2,
            ),
        ],
    )
    def test_import_from_yaml(self, bk_service, bk_plan, input_, expected):
        data = list(yaml.safe_load_all(input_))
        assert PreCreatedInstance.objects.filter(plan=bk_plan).count() == 0
        slz = PreCreatedInstanceImportSLZ(
            data=data, context={"service": bk_service, "tenant_id": DEFAULT_TENANT_ID}, many=True
        )
        slz.is_valid(raise_exception=True)
        slz.save()
        assert PreCreatedInstance.objects.filter(plan=bk_plan).count() == expected

    @pytest.mark.parametrize(
        "input_",
        [
            {"plan": "plan-b", "config": {}, "credentials": DUMMY_CREDENTIALS},
            {"plan": "plan-b", "config": {"a": "b"}, "credentials": DUMMY_CREDENTIALS},
        ],
    )
    def test_import_with_multi_tenant(self, bk_service, bk_plan, input_):
        G(Plan, config="{}", service=bk_service, name="plan-b", tenant_id="test1")
        G(Plan, config="{}", service=bk_service, name="plan-b", tenant_id="test2")
        assert PreCreatedInstance.objects.filter(plan=bk_plan).count() == 0
        slz = PreCreatedInstanceImportSLZ(data=input_, context={"service": bk_service, "tenant_id": DEFAULT_TENANT_ID})
        slz.is_valid(raise_exception=True)
        slz.save()

        assert PreCreatedInstance.objects.filter(plan=bk_plan).count() == 1
        instance = PreCreatedInstance.objects.get(plan=bk_plan)
        assert instance.config == input_["config"]
        assert json.loads(instance.credentials) == json.loads(DUMMY_CREDENTIALS)
