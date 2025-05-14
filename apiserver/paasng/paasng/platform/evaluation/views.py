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

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.evaluation.models import IdleAppNotificationMuteRule


class IdleAppNotificationMuteRuleViewSet(ApplicationCodeInPathMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def create(self, request, **kwargs):
        """新建闲置应用通知屏蔽规则（六个月）"""
        app = self.get_application()
        module = self.get_module_via_path()
        env = self.get_env_via_path()

        rule, _ = IdleAppNotificationMuteRule.objects.update_or_create(
            user=request.user,
            app_code=app.code,
            module_name=module.name,
            environment=env.environment,
            defaults={
                "expired_at": timezone.now() + timedelta(days=180),
                "tenant_id": app.tenant_id,
            },
        )

        return Response(status=status.HTTP_201_CREATED)
