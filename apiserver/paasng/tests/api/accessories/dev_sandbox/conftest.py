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

from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.sourcectl.models import VersionInfo


@pytest.fixture()
def bk_dev_sandbox(bk_cnative_app, bk_module, bk_user) -> DevSandbox:
    version_info = VersionInfo(revision="...", version_name="master", version_type="branch")
    return DevSandbox.objects.create(
        module=bk_module,
        owner=bk_user,
        env_vars={},
        version_info=version_info,
        enable_code_editor=True,
    )
