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
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.engine.serializers import ListConfigVarsQuerySLZ, PresetEnvVarSLZ


class PresetConfigVarViewSet(mixins.ListModelMixin, viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    pagination_class = None
    serializer_class = PresetEnvVarSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    queryset = PresetEnvVariable.objects.all()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        slz = ListConfigVarsQuerySLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        if environment_name := query_params.get("environment_name"):
            queryset = queryset.filter(environment_name=environment_name)

        return queryset.order_by(query_params["order_by"])

    @swagger_auto_schema(
        query_serializer=ListConfigVarsQuerySLZ(),
        tags=["预设环境变量"],
        responses={200: PresetEnvVarSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        module = self.get_module_via_path()
        self.queryset = self.queryset.filter(module=module)
        return super().list(request, *args, **kwargs)
