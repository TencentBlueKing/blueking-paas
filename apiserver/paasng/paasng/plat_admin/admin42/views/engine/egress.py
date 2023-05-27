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
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.egress.models import EgressRule, EgressSpec
from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.egress import EgressSpecSLZ
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes


class EgressManageView(ApplicationDetailBaseView):
    name = "Egress 管理"
    template_name = "admin42/applications/detail/engine/egress.html"


class EgressManageViewSet(ListModelMixin, GenericViewSet, ApplicationCodeInPathMixin):
    """Egress 管理 API"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get(self, request, code, module_name, environment):
        """获取 Egress 配置"""
        wl_app = self.get_wl_app_via_path()
        spec = EgressSpec.objects.filter(wl_app=wl_app).first()
        if not spec:
            return Response(data={"enabled": False})

        return Response(
            data={
                "enabled": True,
                "replicas": spec.replicas,
                "cpu_limit": spec.cpu_limit,
                "memory_limit": spec.memory_limit,
                "rules": [{"host": r.host, "port": r.dst_port, "protocol": r.protocol} for r in spec.rules.all()],
            }
        )

    def create(self, request, code, module_name, environment):
        """创建/更新 Egress 配置"""
        slz = EgressSpecSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        # 1. 检查当前环境所在集群是否支持 Egress IP
        wl_app = self.get_wl_app_via_path()
        cluster = get_cluster_by_app(wl_app)

        if not cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_EGRESS_OPERATOR):
            raise error_codes.FEATURE_FLAG_DISABLED.f(_('当前环境所部署的集群不支持 BCS Egress'))

        # 2. 检查是否有现存的配置，如果有则对比并更新，否则全部新建
        egress_spec = EgressSpec.objects.filter(wl_app=wl_app).first()
        if egress_spec:
            # 更新 egress_spec
            egress_spec.replicas = slz.data['replicas']
            egress_spec.cpu_limit = slz.data['cpu_limit']
            egress_spec.memory_limit = slz.data['memory_limit']
            egress_spec.save()
            # 现存的 EgressRule 都删光光，重新创建
            EgressRule.objects.filter(spec=egress_spec).delete()
        else:
            egress_spec = EgressSpec.objects.create(
                wl_app=wl_app,
                replicas=slz.data['replicas'],
                cpu_limit=slz.data['cpu_limit'],
                memory_limit=slz.data['memory_limit'],
            )

        # 批量创建规则，src/dst 的 host/port 保持一致
        rules = [
            EgressRule(
                spec=egress_spec,
                dst_port=r['port'],
                host=r['host'],
                protocol=r['protocol'],
                src_port=r['port'],
                service=r['host'],
            )
            for r in slz.data['rules']
        ]
        EgressRule.objects.bulk_create(rules)

        # 3. 下发 Egress 到 k8s 集群
        # TODO 下发 Egress 到 k8s 集群，支持更新或者创建

        return Response(status=status.HTTP_201_CREATED)

    def destroy(self, request, code, module_name, environment):
        wl_app = self.get_wl_app_via_path()
        egress_spec = EgressSpec.objects.filter(wl_app=wl_app).first()
        if egress_spec:
            # TODO 从集群中删除 egress 资源
            egress_spec.delete()

        return Response(status.HTTP_200_OK)

    def get_egress_ips(self, request, code, module_name, environment):
        # TODO 从集群中获取 egress pod 的 ip
        return Response(
            data={
                'ips': [
                    '127.0.0.1',
                    '127.0.0.2',
                    '127.0.0.3',
                ]
            }
        )
