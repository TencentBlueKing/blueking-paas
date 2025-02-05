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
from django.utils import timezone

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxStatus
from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.constants import VersionType
from paasng.platform.sourcectl.models import VersionInfo
from tests.utils.helpers import generate_random_string


@pytest.fixture
def dev_sandbox(bk_cnative_app, bk_module, bk_user) -> DevSandbox:
    """测试沙箱"""
    return get_or_create_dev_sandbox(bk_module, bk_user.username)


def get_or_create_dev_sandbox(bk_module: Module, operator: str) -> DevSandbox:
    return DevSandbox.objects.get_or_create(
        module=bk_module,
        owner=operator,
        defaults={
            "code": generate_random_string(length=8),
            "status": DevSandboxStatus.ACTIVE,
            "expired_at": timezone.now() + timezone.timedelta(hours=2),
            "version_info": VersionInfo(
                revision="076b5a580bb999cc4a39c594ae3973409c1d7195",
                version_name="develop",
                version_type=VersionType.BRANCH,
            ),
            "tenant_id": bk_module.tenant_id,
        },
    )
