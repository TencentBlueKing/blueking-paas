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
from django.db.models import Q

from paasng.bk_plugins.pluginscenter.iam_adaptor.policy.converter import PluginPolicyConverter


class TestPluginPolicyConverter:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            ({"field": "plugin.id", "op": "eq", "value": "saas:plugin-1"}, Q(id="plugin-1", pd__identifier="saas")),
            (
                {"field": "plugin.id", "op": "in", "value": ["saas:plugin-1", "udc:plugin-2"]},
                Q(id="plugin-1", pd__identifier="saas") | Q(id="plugin-2", pd__identifier="udc"),
            ),
        ],
    )
    def test_convert(self, data, expected):
        converter = PluginPolicyConverter()
        assert converter.convert(data) == expected
