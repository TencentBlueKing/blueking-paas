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

from paasng.bk_plugins.pluginscenter.iam_adaptor.migrator import IAMPermissionTemplateRender


class TestIAMPermissionTemplateRender:
    def test(self, settings):
        settings.IAM_PLUGINS_CENTER_SYSTEM_ID = "foo"
        settings.BK_IAM_RESOURCE_API_HOST = "api_host"
        template_str = """
        {
            "system_id": "{{ IAM_PLUGINS_CENTER_SYSTEM_ID }}",
            "operations": [
            {
                "data": {
                    "provider_config": {
                        "host": "{{ IAM_RESOURCE_API_HOST }}"
                    }
                }
            }
            ]
        }
        """
        render = IAMPermissionTemplateRender(template_str)
        assert render.render() == {
            "system_id": "foo",
            "operations": [{"data": {"provider_config": {"host": "api_host"}}}],
        }

    @pytest.mark.parametrize(
        "template_str",
        [
            "",
            "[]",
            "{}",
            '{"system_id": "", "operation": {}}',
        ],
    )
    def test_invalid_template(self, template_str):
        render = IAMPermissionTemplateRender(template_str)
        with pytest.raises(ValueError, match=r".*is not a valid.*"):
            render.render()
