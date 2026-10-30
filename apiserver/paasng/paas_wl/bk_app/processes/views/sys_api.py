# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""应用态 (系统 API) 进程视图

这些接口注册在 `sys/api/` 路径下, 仅供 AIDEV 等固定的系统调用, 鉴权依赖 sysapi_client.
"""

import logging

from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.processes.controllers import ProcessesInfo
from paas_wl.bk_app.processes.serializers import ListWatcherRespSLZ, SysUpdateProcessSLZ
from paas_wl.bk_app.processes.watch import ProcInstByEnvListWatcher
from paas_wl.utils.error_codes import error_codes
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.misc.audit.constants import AccessType
from paasng.platform.applications.mixins import SysManagedAppInPathMixin

from .api import do_update_process, list_processes_of_env

logger = logging.getLogger(__name__)


class SysProcessesViewSet(GenericViewSet, SysManagedAppInPathMixin):
    """应用态进程操作接口，目前仅支持 AIDEV 启停 / 扩缩容 AI Agent 应用的进程。"""

    permission_classes = [sysapi_client_perm_class(ClientAction.MANAGE_AI_AGENT_PROCESS)]

    @swagger_auto_schema(
        request_body=SysUpdateProcessSLZ,
        tags=["部署相关接口"],
        operation_id="sys_update_process",
    )
    def update(self, request, code, module_name, environment):
        """应用态操作进程，仅 AIDEV 可调用，仅允许操作 AI Agent 应用。"""
        slz = SysUpdateProcessSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module_env = self.get_managed_env_via_path()
        if module_env.is_offlined:
            logger.warning("Unable to update process, environment %s has gone offline.", module_env)
            raise error_codes.CANNOT_OPERATE_PROCESS.f(_("环境未就绪或已下架, 请尝试重新部署"))

        operator = user_id_encoder.encode(settings.USER_TYPE, data["operator"])
        return Response(
            status=status.HTTP_200_OK,
            data=do_update_process(
                module_env,
                module_env.wl_app,
                operator=operator,
                process_type=data["process_type"],
                operate_type=data["operate_type"],
                autoscaling=data["autoscaling"],
                target_replicas=data.get("target_replicas"),
                scaling_config=data.get("scaling_config"),
                access_type=AccessType.API,
            ),
        )


class SysListAndWatchProcsViewSet(GenericViewSet, SysManagedAppInPathMixin):
    """应用态进程查询接口，目前仅支持 AIDEV 查询 AI Agent 应用。

    不做任何用户维度的权限校验，调用方需要通过 sysapi 客户端权限保证安全。
    """

    permission_classes = [sysapi_client_perm_class(ClientAction.READ_AI_AGENT_APP)]

    @swagger_auto_schema(
        response_serializer=ListWatcherRespSLZ,
        tags=["部署相关接口"],
        operation_id="sys_list_processes",
    )
    def list(self, request, code, module_name, environment):
        """应用态获取当前进程与进程实例实际状态，仅 AIDEV 可调用，仅允许查询 AI Agent 应用。"""
        env = self.get_managed_env_via_path()
        # 使用隔离沙箱的应用由 CR 直接渲染 Pod, 不存在对应的 Deployment, 需要按实例构造进程状态;
        # namespace 级读取会包含同命名空间内其它应用的实例, 按路径对应的 wl_app 过滤
        if env.application.use_isolated_sandbox:
            processes_status = ProcInstByEnvListWatcher(env.application, env.environment).list_instances_only()
            processes_status = ProcessesInfo(
                processes=[p for p in processes_status.processes if p.app.pk == env.wl_app.pk],
                rv_proc=processes_status.rv_proc,
                rv_inst=processes_status.rv_inst,
            )
        else:
            processes_status = None
        return list_processes_of_env(request, env, env.wl_app, processes_status=processes_status)
