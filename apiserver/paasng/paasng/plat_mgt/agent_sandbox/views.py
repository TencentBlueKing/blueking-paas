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

from dataclasses import asdict

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.platform.agent_sandbox.e2b import templates
from paasng.platform.agent_sandbox.e2b.exceptions import E2BTemplateAlreadyExists, E2BTemplateInUse
from paasng.platform.agent_sandbox.e2b.serializers import (
    E2BBuiltinTemplateCreateInputSLZ,
    E2BBuiltinTemplateUpdateInputSLZ,
)
from paasng.platform.agent_sandbox.e2b.template_sync import get_cluster_overviews, get_template_overviews, sync_all
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate
from paasng.utils.error_codes import error_codes

from .serializers import (
    BuiltinTemplateOutputSLZ,
    ClusterSyncOverviewOutputSLZ,
    TemplateSyncOverviewOutputSLZ,
    TemplateSyncOverviewQuerySLZ,
    TemplateSyncResultOutputSLZ,
)


class E2BBuiltinTemplateViewSet(viewsets.GenericViewSet):
    """平台管理-e2b 沙箱内置模板。

    内置模板对所有应用可用，保存后异步下发到所有启用 e2b 的集群，下发状态见 ``E2BTemplateSyncViewSet``。
    """

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.agent_sandbox"],
        operation_description="获取内置模板列表",
        responses={status.HTTP_200_OK: BuiltinTemplateOutputSLZ(many=True)},
    )
    def list(self, request):
        items = E2BSandboxTemplate.objects.builtins()
        return Response(BuiltinTemplateOutputSLZ(items, many=True).data)

    @swagger_auto_schema(
        tags=["plat_mgt.agent_sandbox"],
        operation_description="获取内置模板详情",
        responses={status.HTTP_200_OK: BuiltinTemplateOutputSLZ()},
    )
    def retrieve(self, request, template_id):
        return Response(BuiltinTemplateOutputSLZ(self._get_template(template_id)).data)

    @swagger_auto_schema(
        tags=["plat_mgt.agent_sandbox"],
        operation_description="创建内置模板。集群里已有同名的 SandboxPool / SandboxTemplate 时会被覆盖",
        request_body=E2BBuiltinTemplateCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: BuiltinTemplateOutputSLZ()},
    )
    def create(self, request):
        slz = E2BBuiltinTemplateCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            template = templates.create_builtin_template(**data)
        except E2BTemplateAlreadyExists:
            raise error_codes.AGENT_SANDBOX_E2B_TEMPLATE_ALREADY_EXISTS

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.E2B_SANDBOX_TEMPLATE,
            attribute=template.template_id,
            data_after=DataDetail(data=data),
        )
        return Response(BuiltinTemplateOutputSLZ(template).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.agent_sandbox"],
        operation_description="修改内置模板。已预热的实例保持旧配置直到被消耗完，已创建的沙箱不受影响",
        request_body=E2BBuiltinTemplateUpdateInputSLZ(),
        responses={status.HTTP_200_OK: BuiltinTemplateOutputSLZ()},
    )
    def update(self, request, template_id):
        template = self._get_template(template_id)
        slz = E2BBuiltinTemplateUpdateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data_before = DataDetail(data=self._audit_data(template))

        templates.update_template(template, **slz.validated_data)

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.E2B_SANDBOX_TEMPLATE,
            attribute=template.template_id,
            data_before=data_before,
            data_after=DataDetail(data=self._audit_data(template)),
        )
        return Response(BuiltinTemplateOutputSLZ(template).data)

    @swagger_auto_schema(
        tags=["plat_mgt.agent_sandbox"],
        operation_description="删除内置模板，并从集群中删除它的 CR。模板下还有未销毁的沙箱时拒绝删除",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, template_id):
        template = self._get_template(template_id)
        data_before = DataDetail(data=self._audit_data(template))

        try:
            templates.delete_template(template)
        except E2BTemplateInUse:
            raise error_codes.AGENT_SANDBOX_E2B_TEMPLATE_IN_USE

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.E2B_SANDBOX_TEMPLATE,
            attribute=template_id,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _get_template(template_id: str) -> E2BSandboxTemplate:
        template = E2BSandboxTemplate.objects.builtins().filter(template_id=template_id).first()
        if template is None:
            raise error_codes.AGENT_SANDBOX_E2B_TEMPLATE_NOT_FOUND
        return template

    @staticmethod
    def _audit_data(template: E2BSandboxTemplate) -> dict:
        return BuiltinTemplateOutputSLZ(template).data


class E2BTemplateSyncViewSet(viewsets.GenericViewSet):
    """平台管理-e2b 沙箱模板的下发状态与手动同步，覆盖内置与自定义模板。

    模板保存时，其目标集群即被置为待同步，下发任务完成后更新为成功或失败。据此：

    - 模板对用户可用：汇总状态为 succeeded，即所有目标集群都已同步成功
    - 集群导入了全部模板：集群的 completed 为 true

    模板只在保存时下发，集群变动不会自动触发，需按以下流程操作：

    - 新增 e2b 集群：登记并启用集群的 e2b 配置（``namespace`` 须与网关绑定的一致），
      此时该集群上的模板都是 missing，调用一次同步接口补齐，直到集群 completed。
      自定义模板只下发到应用租户可分配的集群，所以还要确认集群分配策略已包含该集群
    - 下线 e2b 集群：先确认集群上已没有存活沙箱，停用后它们既查不到也销毁不了；
      再停用集群的 e2b 配置，下发状态里即不再出现该集群。同步接口不会再处理停用的集群，
      集群内已下发的 CR 不会被清理，需要时按标签
      ``paas.bk.tencent.com/managed-by=bkpaas-e2b-template`` 手动删除
    - 修改 ``namespace``：调用同步接口在新命名空间下发，旧命名空间里的 CR 同样需要手动删除
    """

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.agent_sandbox"],
        operation_description=(
            "把全部模板（含自定义模板）同步到全部启用 e2b 的集群，并清理平台下发过、但模板已删除的 CR。"
            "幂等，可重复调用；同步执行，直接返回各集群的结果"
        ),
        responses={status.HTTP_200_OK: TemplateSyncResultOutputSLZ(many=True)},
    )
    def sync(self, request):
        results = sync_all()

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.REFRESH,
            target=OperationTarget.E2B_SANDBOX_TEMPLATE,
            attribute="sync",
        )
        return Response(TemplateSyncResultOutputSLZ([asdict(r) for r in results], many=True).data)

    @swagger_auto_schema(
        tags=["plat_mgt.agent_sandbox"],
        operation_description="按模板查看下发状态",
        query_serializer=TemplateSyncOverviewQuerySLZ(),
        responses={status.HTTP_200_OK: TemplateSyncOverviewOutputSLZ(many=True)},
    )
    def list_templates(self, request):
        slz = TemplateSyncOverviewQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data

        is_builtin = params["is_builtin"]
        if is_builtin is None:
            items = E2BSandboxTemplate.objects.all()
        else:
            items = E2BSandboxTemplate.objects.builtins() if is_builtin else E2BSandboxTemplate.objects.customs()
        items = items.select_related("application").prefetch_related("sync_records")
        overviews = get_template_overviews(list(items))
        if sync_status := params.get("status"):
            overviews = [o for o in overviews if o.status == sync_status]
        return Response(TemplateSyncOverviewOutputSLZ(overviews, many=True).data)

    @swagger_auto_schema(
        tags=["plat_mgt.agent_sandbox"],
        operation_description="按集群查看下发状态，覆盖全部启用 e2b 的集群",
        responses={status.HTTP_200_OK: ClusterSyncOverviewOutputSLZ(many=True)},
    )
    def list_clusters(self, request):
        return Response(ClusterSyncOverviewOutputSLZ(get_cluster_overviews(), many=True).data)
