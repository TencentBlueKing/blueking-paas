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

from typing import Dict

import pytest

from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.deployment.validations.v3 import DeploymentDescSLZ
from paasng.platform.declarative.serializers import validate_desc
from tests.paasng.platform.declarative.utils import AppDescV3Builder as builder  # noqa: N813

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def get_deployment_description(module_desc: Dict) -> DeploymentDesc:
    """A help tool get parse the application json data, describe at app_desc.yml::module part to DeploymentDesc"""
    desc = validate_desc(DeploymentDescSLZ, module_desc)
    return desc


class TestValidateGoodCase:
    """A test suite about v3 validations - good case"""

    def test_normal(self):
        module_desc = builder.make_module(module_name="foo", is_default=True)
        get_deployment_description(module_desc)
