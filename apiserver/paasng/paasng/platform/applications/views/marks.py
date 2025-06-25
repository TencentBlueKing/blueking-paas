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

import logging

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications import serializers as slzs
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import ApplicationDeploymentModuleOrder, UserMarkedApplication
from paasng.platform.modules.models.module import Module

logger = logging.getLogger(__name__)


class ApplicationMarkedViewSet(viewsets.ModelViewSet):
    """
    用户标记的应用
    list: 获取用户标记的应用列表
    - [测试地址](/api/bkapps/accounts/marked_applications/)
    create: 添加标记应用
    - [测试地址](/api/bkapps/accounts/marked_applications/)
    retrieve: 获取标记详情
    - [测试地址](/api/bkapps/accounts/marked_applications/)
    destroy: 删除标记
    - [测试地址](/api/bkapps/accounts/marked_applications/)
    """

    lookup_field = "code"
    serializer_class = slzs.ApplicationMarkedSLZ
    queryset = UserMarkedApplication.objects.all()
    pagination_class = None

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user.pk)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly." % (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {"application__code": self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class ApplicationDeploymentModuleOrderViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """部署管理-进程列表，模块的排序"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(request_body=slzs.ApplicationDeploymentModuleOrderReqSLZ)
    @transaction.atomic
    def upsert(self, request, code):
        """设置模块的排序"""
        serializer = slzs.ApplicationDeploymentModuleOrderReqSLZ(data=request.data, context={"code": code})
        serializer.is_valid(raise_exception=True)
        module_orders_data = serializer.validated_data["module_orders"]

        application = self.get_application()
        modules = Module.objects.filter(application=application)
        module_name_to_module_dict = {module.name: module for module in modules}

        # 操作前
        old_module_orders = list(
            ApplicationDeploymentModuleOrder.objects.filter(user=request.user.pk, module__application=application)
            .order_by("order")
            .values("order", module_name=F("module__name"))
        )

        # 更新或创建模块排序
        for item in module_orders_data:
            ApplicationDeploymentModuleOrder.objects.update_or_create(
                user=request.user.pk,
                module=module_name_to_module_dict[item["module_name"]],
                defaults={
                    "order": item["order"],
                    "tenant_id": application.tenant_id,
                },
            )

        # 操作后
        new_module_orders = list(
            ApplicationDeploymentModuleOrder.objects.filter(user=request.user.pk, module__application=application)
            .order_by("order")
            .values("order", module_name=F("module__name"))
        )

        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.MODULE,
            result_code=ResultCode.SUCCESS,
            data_before=DataDetail(data=old_module_orders),
            data_after=DataDetail(data=new_module_orders),
        )

        serializer = slzs.ApplicationDeploymentModuleOrderSLZ(new_module_orders, many=True)
        return Response(serializer.data)

    def list(self, request, code):
        """获取模块的排序"""
        application = self.get_application()
        result = (
            ApplicationDeploymentModuleOrder.objects.filter(user=request.user.pk, module__application=application)
            .order_by("order")
            .values("order", module_name=F("module__name"))
        )
        serializer = slzs.ApplicationDeploymentModuleOrderSLZ(result, many=True)
        return Response(serializer.data)
