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

from paasng.platform.bkapp_model.entities import AppBuildConfig
from paasng.platform.bkapp_model.syncer import sync_build
from paasng.platform.modules.models import BuildConfig

pytestmark = pytest.mark.django_db


class Test__sync_build:
    def test(self, bk_module):
        sync_build(bk_module, AppBuildConfig(image="example.com/foo", image_credentials_name="foo"))
        cfg = BuildConfig.objects.get(module=bk_module)
        assert cfg.image_repository == "example.com/foo"
        assert cfg.image_credential_name == "foo"
