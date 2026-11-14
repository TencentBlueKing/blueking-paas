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

from typing import Any, Dict

from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.models import Cluster, ClusterE2BConfig
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterE2BConfigRetrieveOutputSLZ,
    ClusterE2BConfigUpsertInputSLZ,
)
from paasng.platform.agent_sandbox.e2b.clusters import count_live_sandboxes
from paasng.platform.agent_sandbox.e2b.template_sync.sync import forget_cluster
from paasng.utils.error_codes import error_codes


class ClusterE2BConfigViewSet(viewsets.GenericViewSet):
    """集群 e2b 沙箱接入配置"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    lookup_field = "name"
    lookup_url_kwarg = "cluster_name"

    def get_queryset(self):
        # FIXME: (多租户) 根据平台/租户管理员身份，返回不同的集群列表
        return Cluster.objects.all()

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_e2b_config"],
        operation_description="获取集群 e2b 沙箱配置，未配置时返回 404",
        responses={status.HTTP_200_OK: ClusterE2BConfigRetrieveOutputSLZ()},
    )
    def retrieve(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()
        config = ClusterE2BConfig.objects.filter(cluster=cluster).first()
        if not config:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(data=ClusterE2BConfigRetrieveOutputSLZ(config).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_e2b_config"],
        operation_description="新建或更新集群 e2b 沙箱配置",
        request_body=ClusterE2BConfigUpsertInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def upsert(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()
        config = ClusterE2BConfig.objects.filter(cluster=cluster).first()
        data_before = DataDetail(data=self._to_audit_data(config)) if config else None

        slz = ClusterE2BConfigUpsertInputSLZ(data=request.data, context={"cur_config": config})
        slz.is_valid(raise_exception=True)

        config, created = ClusterE2BConfig.objects.update_or_create(
            cluster=cluster, defaults={**slz.validated_data, "tenant_id": cluster.tenant_id}
        )

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE if created else OperationEnum.MODIFY,
            target=OperationTarget.CLUSTER,
            attribute=f"{cluster.name}/e2b_config",
            data_before=data_before,
            data_after=DataDetail(data=self._to_audit_data(config)),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_e2b_config"],
        operation_description="删除集群 e2b 沙箱配置",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, cluster_name, *args, **kwargs):
        cluster = self.get_object()
        config = ClusterE2BConfig.objects.filter(cluster=cluster).first()
        if not config:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if live_count := count_live_sandboxes(cluster.name):
            raise error_codes.CANNOT_DELETE_CLUSTER_E2B_CONFIG.f(
                _("集群上仍有 {} 个存活的 e2b 沙箱，请先停用配置，待存量沙箱全部销毁后再删除").format(live_count)
            )

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.CLUSTER,
            attribute=f"{cluster.name}/e2b_config",
            data_before=DataDetail(data=self._to_audit_data(config)),
        )
        config.delete()
        forget_cluster(cluster.name)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _to_audit_data(config: ClusterE2BConfig) -> Dict[str, Any]:
        return dict(ClusterE2BConfigRetrieveOutputSLZ(config).data)
