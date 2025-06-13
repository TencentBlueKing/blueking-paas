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

from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.networking.egress.models import RCStateAppBinding, RegionClusterState
from paas_wl.workloads.networking.egress.serializers import RCStateAppBindingSLZ
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin

logger = logging.getLogger(__name__)


class EgressGatewayInfosViewSet(ApplicationCodeInPathMixin, GenericViewSet):
    """应用出口 IP 管理相关 API"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def retrieve(self, request, code, module_name, environment):
        """返回已获取的出口网关信息"""
        wl_app = self.get_wl_app_via_path()
        binding = get_object_or_404(RCStateAppBinding, app=wl_app)
        serializer = RCStateAppBindingSLZ(binding)
        return Response(
            {
                # Use 'default' as name of the default egress gateway info for all environments
                "name": "default",
                "rcs_binding_data": serializer.data,
            }
        )

    def create(self, request, code, module_name, environment):
        """绑定应用在该部署环境下的出口网关信息"""
        # 由于该 Egress 实现导致 Pod 仅能调度在指定节点，对于集群运维极其不利，因此决定禁用增量的 RegionClusterState 配置
        # 如果还是有开启的需求，应该由平台管理员，使用 python manage.py create_rc_state_binding 命令添加
        application = self.get_application()
        if not application.feature_flag.has_feature(AppFeatureFlag.TOGGLE_EGRESS_BINDING):
            raise error_codes.EDITION_NOT_SUPPORT.f(_("新建出口 IP 绑定功能已禁用，如有需要请联系管理员"))

        wl_app = self.get_wl_app_via_path()

        cluster = get_cluster_by_app(wl_app)
        try:
            state = RegionClusterState.objects.filter(cluster_name=cluster.name).latest()
            binding = RCStateAppBinding.objects.create(app=wl_app, state=state, tenant_id=cluster.tenant_id)
        except RegionClusterState.DoesNotExist:
            logger.warning("No cluster state can be found for cluster=%s", cluster.name)
            raise error_codes.ERROR_ACQUIRING_EGRESS_GATEWAY_INFO.f("集群数据未初始化，请稍候再试")
        except IntegrityError:
            raise error_codes.ERROR_ACQUIRING_EGRESS_GATEWAY_INFO.f("不能重复绑定")
        except Exception:
            logger.exception("Unable to crate RCStateBinding instance")
            raise error_codes.ERROR_ACQUIRING_EGRESS_GATEWAY_INFO.f("请稍候再试")

        serializer = RCStateAppBindingSLZ(binding)

        add_app_audit_record(
            app_code=code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE,
            target=OperationTarget.EXIT_IP,
            module_name=module_name,
            environment=environment,
            data_after=DataDetail(data=serializer.data),
        )
        return Response({"name": "default", "rcs_binding_data": serializer.data}, status=status.HTTP_201_CREATED)

    def destroy(self, request, code, module_name, environment):
        """清除已获取的出口网关信息"""
        wl_app = self.get_wl_app_via_path()
        try:
            binding = RCStateAppBinding.objects.get(app=wl_app)
        except RCStateAppBinding.DoesNotExist:
            raise error_codes.ERROR_RECYCLING_EGRESS_GATEWAY_INFO.f("未获取过网关信息")
        data_before = DataDetail(data=RCStateAppBindingSLZ(binding).data)
        binding.delete()

        add_app_audit_record(
            app_code=code,
            tenant_id=wl_app.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.DELETE,
            target=OperationTarget.EXIT_IP,
            module_name=module_name,
            environment=environment,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
