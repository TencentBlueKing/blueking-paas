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
import logging
from typing import List

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paasng.bk_plugins.pluginscenter import constants, serializers, shim
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ItsmTicketStatus
from paasng.bk_plugins.pluginscenter.itsm_adaptor.open_apis.authentication import ItsmBasicAuthentication
from paasng.bk_plugins.pluginscenter.models import PluginInstance

logger = logging.getLogger(__name__)


class PluginCallBackApiViewSet(GenericViewSet):
    authentication_classes = (ItsmBasicAuthentication,)
    permission_classes: List = []

    def get_plugin_instance(self) -> PluginInstance:
        queryset = PluginInstance.objects.all()
        filter_kwargs = {"pd__identifier": self.kwargs["pd_id"], "id": self.kwargs["plugin_id"]}  # type: ignore
        obj = get_object_or_404(queryset, **filter_kwargs)
        return obj

    def itsm_stage_callback(self, request, pd_id, plugin_id, release_id, stage_id):
        """发布流程中上线审批阶段回调, 更新审批阶段的状态"""
        serializer = serializers.ItsmApprovalSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        plugin = self.get_plugin_instance()
        release = plugin.all_versions.get(pk=release_id)
        stage = release.all_stages.get(id=stage_id)

        # 根据 itsm 的回调结果更新单据状态
        ticket_status = serializer.validated_data["current_status"]
        approve_result = serializer.validated_data["approve_result"]
        stage_status = self._convert_release_status(ticket_status, approve_result)
        stage.status = stage_status
        stage.save(update_fields=["status", "updated"])
        return Response({"message": "success", "code": 0, "data": None, "result": True})

    def itsm_create_callback(self, request, pd_id, plugin_id):
        """创建插件审批回调，更新插件状态并完成插件创建相关操作"""
        logger.error("itsm test, request.data: %s", request.data)
        serializer = serializers.ItsmApprovalSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        plugin = self.get_plugin_instance()

        ticket_status = serializer.validated_data["current_status"]
        approve_result = serializer.validated_data["approve_result"]
        plugin_status = self._convert_create_status(ticket_status, approve_result)

        # 审批成功，则更新插件状态并完成插件创建相关操作
        if plugin_status == constants.PluginStatus.DEVELOPING:
            # 完成创建插件的剩余操作
            shim.init_plugin_in_view(plugin, plugin.creator.username)
        # 更新插件的状态
        plugin.status = plugin_status
        plugin.save(update_fields=["status", "updated"])
        return Response({"message": "success", "code": 0, "data": None, "result": True})

    def _convert_release_status(
        self, ticket_status: ItsmTicketStatus, approve_result: bool
    ) -> constants.PluginReleaseStatus:
        """将ITSM单据状态和结果转换为插件版本 Stage 的状态"""
        status = constants.PluginReleaseStatus.PENDING
        if ticket_status == ItsmTicketStatus.FINISHED:
            # 单据结束，则审批阶段的状态则对应地设置为成功、失败
            status = (
                constants.PluginReleaseStatus.SUCCESSFUL if approve_result else constants.PluginReleaseStatus.FAILED
            )
        elif ticket_status in [ItsmTicketStatus.TERMINATED, ItsmTicketStatus.REVOKED]:
            # 单据被撤销，则审批阶段状态设置为已中断
            status = constants.PluginReleaseStatus.INTERRUPTED

        return status

    def _convert_create_status(self, ticket_status: ItsmTicketStatus, approve_result: bool) -> constants.PluginStatus:
        """将ITSM单据状态和结果转换为插件状态"""
        status = constants.PluginStatus.APPROVAL_FAILED
        if ticket_status == ItsmTicketStatus.FINISHED and approve_result:
            # 单据结束且结果为审批成功，则插件状态设置为开发中，否则为审批失败状态
            status = constants.PluginStatus.DEVELOPING

        return status
