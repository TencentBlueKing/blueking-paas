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
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from paasng.platform.evaluation.models import IdleAppNotificationMuteRule

pytestmark = pytest.mark.django_db


class TestIdleAppNotificationMuteRuleViewSet:
    def test_create(self, bk_user, api_client, bk_app, bk_module, bk_stag_env):
        resp = api_client.post(
            path=f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}"
            + f"/envs/{bk_stag_env.environment}/idle_notification/mute_rules/"
        )
        assert resp.status_code == status.HTTP_201_CREATED

        rule = IdleAppNotificationMuteRule.objects.filter(
            user=bk_user, app_code=bk_app.code, module_name=bk_module.name, environment=bk_stag_env.environment
        ).first()

        assert rule is not None
        assert rule.expired_at.date() == (timezone.now() + timedelta(days=180)).date()
