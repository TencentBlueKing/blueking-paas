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

from paasng.platform.declarative.deployment.resources import BkSaaSItem
from paasng.platform.declarative.deployment.svc_disc import BkSaaSAddrDiscoverer

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestBkSaaSEnvVariableFactoryExtendWithClusterApp:
    def test_missing_app(self):
        items = [
            BkSaaSItem(bk_app_code="foo-app"),
            BkSaaSItem(bk_app_code="foo-app", module_name="bar-module"),
        ]
        # clusters 类型为 Dict，这里直接判断是否为空
        cluster_states = [bool(clusters) for _, clusters in BkSaaSAddrDiscoverer.extend_with_clusters(items)]
        # App which is not existed in the database should not has any cluster
        # object returned.
        assert cluster_states == [False, False]

    def test_existed_app(self, bk_app, bk_module):
        items = [
            BkSaaSItem(bk_app_code=bk_app.code),
            BkSaaSItem(bk_app_code=bk_app.code, module_name=bk_module.name),
            BkSaaSItem(bk_app_code=bk_app.code, module_name="wrong-name"),
        ]
        cluster_states = [bool(clusters) for _, clusters in BkSaaSAddrDiscoverer.extend_with_clusters(items)]
        # Item which did not specify module_name and specified a right module name
        # should has a cluster object returned.
        assert cluster_states == [True, True, False]
