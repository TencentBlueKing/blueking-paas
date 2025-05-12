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

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID, get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.clusters.serializers import ClusterDefaultConfigListOutputSLZ


class ClusterDefaultConfigViewSet(viewsets.GenericViewSet):
    """集群默认配置相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_default_configs"],
        operation_description="集群默认配置",
        responses={status.HTTP_200_OK: ClusterDefaultConfigListOutputSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        # 默认当前集群不能使用平台默认镜像仓库
        image_repository = ""
        # 如果集群是默认 / 运营租户下的，则允许使用平台默认镜像仓库
        if get_tenant(request.user).id in [DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID]:
            image_repository = f"{settings.APP_DOCKER_REGISTRY_HOST}/{settings.APP_DOCKER_REGISTRY_NAMESPACE}"

        defaults = {"image_repository": image_repository, "feature_flags": ClusterFeatureFlag.get_default_flags()}
        return Response(ClusterDefaultConfigListOutputSLZ(defaults).data)
