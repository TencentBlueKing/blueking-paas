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

from pathlib import Path

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db


class TestProcessComponentViewSet:
    """测试进程组件视图集"""

    @pytest.fixture(autouse=True)
    def _mock_components_dir(self, monkeypatch):
        test_dir = Path(settings.BASE_DIR) / "tests" / "support-files" / "test_components"
        monkeypatch.setattr("paasng.accessories.proc_components.manager.DEFAULT_COMPONENT_DIR", test_dir)

    def test_list(self, api_client):
        """测试获取进程组件列表"""
        resp = api_client.get("/api/proc_components")
        assert resp.status_code == 200
        assert resp.data == [
            {
                "name": "test_env_overlay",
                "version": "v1",
                "schema": {
                    "type": "object",
                    "required": ["env"],
                    "properties": {
                        "env": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name", "value"],
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "value": {"type": "string"},
                                },
                                "additionalProperties": False,
                            },
                            "minItems": 1,
                        }
                    },
                    "additionalProperties": False,
                },
                "documentation": "test_env_overlay\n",
            },
            {
                "name": "test_sidecar",
                "version": "v1",
                "schema": {"description": "不需要任何参数", "type": "object", "additionalProperties": False},
                "documentation": "test_sidecar\n",
            },
        ]
