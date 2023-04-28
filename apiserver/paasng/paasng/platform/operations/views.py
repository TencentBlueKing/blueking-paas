# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from collections import namedtuple
from typing import List

from django.conf import settings
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import UserApplicationFilter
from paasng.platform.applications.views import ApplicationCodeInPathMixin
from paasng.platform.operations import serializers
from paasng.platform.operations.serializers import RecentOperationsByAppSLZ
from paasng.publish.entrance.exposer import get_module_exposed_links

from .constant import OperationType as OT
from .models import ApplicationLatestOp, Operation
from .serializers import QueryRecentOperatedApplications

EventRepresentProps = namedtuple('EventRepresentProps', 'display_module provide_links provide_actions')


class OperationRepresentHelper:
    """Helps representing an application operation to user"""

    _type_props_map = {
        # "type: [display_module, provide_links, provide_actions]"
        OT.CREATE_APPLICATION: [False, False, True],
        OT.REGISTER_PRODUCT: [False, True, True],
        OT.MODIFY_PRODUCT_ATTRIBUTES: [False, True, True],
        OT.OFFLINE_MARKET: [False, True, True],
        OT.RELEASE_TO_MARKET: [False, True, True],
        OT.CREATE_MODULE: [False, False, True],
        OT.PROCESS_START: [True, True, True],
        OT.PROCESS_STOP: [True, True, True],
        OT.OFFLINE_APPLICATION_STAG_ENVIRONMENT: [True, True, True],
        OT.OFFLINE_APPLICATION_PROD_ENVIRONMENT: [True, True, True],
        OT.DEPLOY_APPLICATION: [True, True, True],
    }
    type_props_map = {k.value: v for k, v in _type_props_map.items()}

    def get_supported_types(self) -> List[int]:
        """All supported types"""
        return list(self.type_props_map.keys())

    def get_event_props(self, event_type: int) -> EventRepresentProps:
        """Get event properties by event_type"""
        values = self.type_props_map[event_type]
        return EventRepresentProps(*values)


class LatestApplicationsViewSet(APIView):
    """
    最近操作的应用列表
    get: 最近操作的应用列表
    - [测试地址](/api/bkapps/applications/lists/latest/)
    - 已经按照application去重
    - 接口返回的顺序为按操作时间逆序
    - 如果需要调整返回的应用数，通过limit参数指定（后台限制最大10个）, 如http://paas.bking.com/api/bkapps/applications/latest/?limit=5
    """

    serializer_class = serializers.OperationSLZ
    lookup_field = "id"
    ordering_fields = ('-id',)
    pagination_class = None

    def get_queryset(self, limit: int):
        helper = OperationRepresentHelper()
        op_types = helper.get_supported_types()

        applications = UserApplicationFilter(self.request.user).filter()
        # 插件开发者中心正式上线前需要根据配置来决定应用列表中是否展示插件应用
        if not settings.DISPLAY_BK_PLUGIN_APPS:
            applications = applications.exclude(type=ApplicationType.BK_PLUGIN)

        application_ids = applications.values_list("id", flat=True)

        latest_operated_objs = (
            ApplicationLatestOp.objects.filter(operation_type__in=op_types, application__id__in=application_ids)
            .select_related('operation')
            .order_by("-latest_operated_at")[:limit]
        )

        # Get operation objects from latest operations
        items = [obj.operation for obj in latest_operated_objs]
        for item in items:
            self._transform_op(item)
            self._attach_represent_info(item)
        return items

    def _transform_op(self, obj: Operation):
        """Transform special operations before representing them to users"""
        # When app's engine was disabled, tranform `CREATE_MODULE` event because engine-less app has no idea what
        # "module" is.
        if not obj.application.engine_enabled:
            if obj.type == OT.CREATE_MODULE.value:
                obj.type = OT.CREATE_APPLICATION.value

    def _attach_represent_info(self, obj: Operation):
        """Attach an extra "represent_info" onto operation object"""
        helper = OperationRepresentHelper()
        event_props = helper.get_event_props(obj.type)
        # Display nothing for applications which has engine disabled
        if not obj.application.engine_enabled:
            event_props = EventRepresentProps(False, False, False)

        module_name = obj.module_name or obj.application.get_default_module().name
        represent_info = {
            'props': event_props._asdict(),
            'module_name': module_name,
        }
        if event_props.provide_links:
            module = obj.application.get_module(module_name)
            represent_info['links'] = get_module_exposed_links(module)

        obj.represent_info = represent_info

    def get(self, request, *args, **kwargs):
        serializer = QueryRecentOperatedApplications(data=request.GET)
        serializer.is_valid(raise_exception=True)

        records_queryset = self.get_queryset(serializer.data['limit'])
        data = {
            "results": records_queryset,
        }
        serializer = RecentOperationsByAppSLZ(data)
        return Response(serializer.data)


class ApplicationOperationsViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """
    单应用的操作记录
    list: 单应用的操作记录
    - [测试地址](/api/bkapps/applications/awesome-app/operations/)
    - 接口返回的顺序为按操作时间逆序
    - 返回记录条数通过limit设置，默认值5
    """

    serializer_class = serializers.ApplicationOperationSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]
    queryset = Operation.objects.all()
    lookup_field = "id"
    ordering_fields = ('-id',)

    def get_queryset(self):
        return self.queryset.filter(application__code=self.kwargs['code'], is_hidden=False).order_by('-id')

    def list(self, request, *args, **kwargs):
        application = self.get_application()
        self.queryset = Operation.objects.filter(application=application)
        # 路径参数中指定了模块才查询模块的操作记录，否则查询应用所有的操作记录
        if module_name := kwargs.get('module_name'):
            self.queryset = self.queryset.filter(module_name=module_name)
        return super().list(request, *args, **kwargs)
