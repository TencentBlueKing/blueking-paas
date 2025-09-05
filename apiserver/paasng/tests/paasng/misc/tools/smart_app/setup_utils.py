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

import string

import pytest

from paasng.misc.tools.smart_app.constants import SourceCodeOriginType
from paasng.misc.tools.smart_app.models import SmartBuildLog, SmartBuildRecord
from paasng.platform.engine.constants import JobStatus
from tests.utils.auth import create_user
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db


def create_fake_smart_build(
    package_name=None,
    app_code=None,
    operator=None,
    status=JobStatus.PENDING.value,
    **kwargs,
):
    """Create a fake SmartBuild instance for testing"""
    if package_name is None:
        package_name = f"{generate_random_string(8)}.tar.gz"
    if app_code is None:
        app_code = generate_random_string(8, string.ascii_lowercase)
    if operator is None:
        operator = create_user()

    log = SmartBuildLog.objects.create()

    return SmartBuildRecord.objects.create(
        source_origin=SourceCodeOriginType.PACKAGE.value,
        package_name=package_name,
        app_code=app_code,
        status=status,
        operator=operator,
        stream=log,
        tenant_id="default",
        **kwargs,
    )
