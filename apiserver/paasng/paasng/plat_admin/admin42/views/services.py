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

from django.db.transaction import atomic
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paasng.accessories.servicehub.constants import LEGACY_PLAN_ID
from paasng.accessories.servicehub.exceptions import (
    SvcAttachmentDoesNotExist,
    UnboundSvcAttachmentDoesNotExist,
)
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.services import EngineAppInstanceRel, UnboundEngineAppInstanceRel
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.services import (
    PlanObjSLZ,
    ServiceInstanceBindInfoSLZ,
    ServiceInstanceSLZ,
    ServiceObjSLZ,
    UnboundServiceInstanceInfoSLZ,
)
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.models import Application
from paasng.utils.error_codes import error_codes


class ApplicationServicesView(ApplicationDetailBaseView):
    """Application应用增强服务页"""

    template_name = "admin42/operation/applications/detail/services.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "增强服务"


class ApplicationServicesManageViewSet(GenericViewSet):
    """应用增强服务管理-服务管理API"""

    schema = None
    serializer_class = ServiceInstanceBindInfoSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    @staticmethod
    def _gen_service_data_detail(rel: EngineAppInstanceRel) -> DataDetail:
        service_data = ServiceObjSLZ(rel.get_service()).data

        return DataDetail(
            data={
                "instance": ServiceInstanceSLZ(rel.get_instance()).data,
                "service": service_data,
                "plan": PlanObjSLZ(rel.get_plan()).data,
            },
        )

    def list(self, request, code):
        service_instance_list = []
        application = get_object_or_404(Application, code=code)
        for module in application.modules.all():
            for env in module.envs.all():
                for rel in mixed_service_mgr.list_all_rels(engine_app=env.engine_app):
                    instance = None
                    if rel.is_provisioned():
                        instance = rel.get_instance()

                    service_instance_list.append(
                        dict(
                            environment=env,
                            module=env.module.name,
                            instance=instance,
                            service=rel.get_service(),
                            plan=rel.get_plan(),
                        )
                    )
        return Response(ServiceInstanceBindInfoSLZ(service_instance_list, many=True).data)

    @atomic
    def provision_instance(self, request, code, module_name, environment, service_id):
        application = get_object_or_404(Application, code=code)
        module = application.get_module(module_name)
        env = module.envs.get(environment=environment)
        service = mixed_service_mgr.get_or_404(service_id)

        rel = next(mixed_service_mgr.list_unprovisioned_rels(env.engine_app, service=service), None)
        if not rel:
            raise error_codes.CANNOT_PROVISION_INSTANCE.f(_("当前环境不存在未分配的增强服务实例"))

        rel.provision()
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.PROVISION_INSTANCE,
            target=OperationTarget.APP,
            app_code=code,
            module_name=module_name,
            environment=environment,
            data_after=self._gen_service_data_detail(rel),
        )
        return Response(status=status.HTTP_201_CREATED)

    @atomic
    def recycle_resource(self, request, code, module_name, service_id, instance_id):
        service = mixed_service_mgr.get_or_404(service_id)

        try:
            instance_rel = mixed_service_mgr.get_instance_rel_by_instance_id(service, instance_id)
        except SvcAttachmentDoesNotExist:
            raise Http404

        # 迁移应用不能回收资源
        # 因为关联的方案不能重新分配实例的方案
        # 迁移前先在 paas2.0的 open_paas 表中将数据库信息修改外预期迁移后的数据库信息后，再开始迁移工作
        if instance_rel.get_plan().uuid == LEGACY_PLAN_ID:
            raise error_codes.FEATURE_FLAG_DISABLED.f(_("迁移应用不支持回收增强服务实例"))

        if instance_rel.is_provisioned():
            data_before = self._gen_service_data_detail(instance_rel)
            instance_rel.recycle_resource()
            add_admin_audit_record(
                user=request.user.pk,
                operation=OperationEnum.RECYCLE_RESOURCE,
                target=OperationTarget.APP,
                app_code=code,
                module_name=module_name,
                data_before=data_before,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationUnboundServicesManageViewSet(GenericViewSet):
    """应用增强服务管理-回收管理API"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    @staticmethod
    def _gen_service_data_detail(rel: UnboundEngineAppInstanceRel) -> DataDetail:
        service_data = ServiceObjSLZ(mixed_service_mgr.get_or_404(rel.db_obj.service_id)).data

        return DataDetail(
            data={
                "instance": ServiceInstanceSLZ(rel.get_instance()).data,
                "service": service_data,
            },
        )

    def list(self, request, code):
        result = []
        application = get_object_or_404(Application, code=code)
        for module in application.modules.all():
            for env in module.envs.all():
                for rel in mixed_service_mgr.list_unbound_instance_rels(engine_app=env.engine_app):
                    instance = rel.get_instance()
                    if not instance:
                        # 如果已经回收了，获取不到 instance，跳过
                        continue

                    result.append(
                        dict(
                            environment=env.environment,
                            module=module.name,
                            instance=instance,
                            service=mixed_service_mgr.get_or_404(rel.db_obj.service_id),
                        )
                    )
        return Response(UnboundServiceInstanceInfoSLZ(result, many=True).data)

    def recycle_resource(self, request, code, module_name, service_id, instance_id):
        service = mixed_service_mgr.get_or_404(service_id)

        try:
            rel = mixed_service_mgr.get_unbound_instance_rel_by_instance_id(service, instance_id)
        except UnboundSvcAttachmentDoesNotExist:
            raise Http404

        data_before = self._gen_service_data_detail(rel)
        rel.recycle_resource()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.RECYCLE_RESOURCE,
            target=OperationTarget.APP,
            app_code=code,
            module_name=module_name,
            data_before=data_before,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
