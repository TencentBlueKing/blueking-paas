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

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template

pytestmark = pytest.mark.django_db


class TestAppSpecs:
    @pytest.mark.parametrize(
        ("type", "value"),
        [
            (ApplicationType.DEFAULT, True),
            (ApplicationType.ENGINELESS_APP, False),
            (ApplicationType.CLOUD_NATIVE, True),
        ],
    )
    def test_engine_enabled(self, type, value, bk_app):
        bk_app.type = type
        bk_app.save(update_fields=["type"])
        assert AppSpecs(bk_app).engine_enabled is value

    @pytest.mark.parametrize(
        ("is_smart_app", "is_plugin_app", "type", "value"),
        [
            (False, False, ApplicationType.DEFAULT, True),
            (False, False, ApplicationType.CLOUD_NATIVE, True),
            (False, False, ApplicationType.ENGINELESS_APP, False),
            # 普通应用、云原生应用的 S-mart 应用，都不能创建模块
            (True, False, ApplicationType.DEFAULT, False),
            (True, False, ApplicationType.CLOUD_NATIVE, False),
            # 普通应用、云原生应用的插件应用，都不能创建模块
            (False, True, ApplicationType.DEFAULT, False),
            (False, True, ApplicationType.CLOUD_NATIVE, False),
        ],
    )
    def test_can_create_extra_modules(self, is_smart_app, is_plugin_app, type, value, bk_app):
        bk_app.type = type
        bk_app.is_smart_app = is_smart_app
        bk_app.is_plugin_app = is_plugin_app
        bk_app.save(update_fields=["type", "is_smart_app", "is_plugin_app"])

        assert AppSpecs(bk_app).can_create_extra_modules is value

    def test_confirm_required_when_publish_with_no_template(self, bk_app):
        confirm_required_when_publish = AppSpecs(bk_app).confirm_required_when_publish
        assert confirm_required_when_publish is False

    @pytest.mark.parametrize(
        ("market_ready", "expect"),
        [
            (True, False),
            (False, True),
        ],
    )
    def test_confirm_required_when_publish_with_template(self, bk_app, market_ready, expect):
        module = bk_app.get_default_module()
        Template.objects.update_or_create(
            name=module.source_init_template,
            type=TemplateType.NORMAL,
            defaults={"market_ready": market_ready, "blob_url": "[]"},
        )
        confirm_required_when_publish = AppSpecs(bk_app).confirm_required_when_publish
        assert confirm_required_when_publish == expect
