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

from typing import Any, Dict, List

from django.db.transaction import atomic
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.servicehub.constants import LEGACY_PLAN_ID
from paasng.accessories.servicehub.exceptions import SvcAttachmentDoesNotExist
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.services import EngineAppInstanceRel, ServiceObj
from paasng.accessories.servicehub.sharing import ServiceSharingManager, SharingReferencesManager
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_mgt.applications.serializers import services as slzs
from paasng.plat_mgt.infras.services.serializers import (
    PlanObjOutputSLZ,
    ServiceInstanceOutputSLZ,
    ServiceObjOutputSLZ,
)
from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module
from paasng.utils.error_codes import error_codes


class ApplicationServicesViewSet(viewsets.ViewSet):
    """平台管理 - 应用增强服务"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_200_OK: slzs.ServiceListOutputSLZ(many=True)},
    )
    def list_bound_attachments(self, request, code):
        """列出已绑定的增强服务"""

        application = get_object_or_404(Application, code=code)
        modules_data = []

        for module in application.modules.all():
            # 查询共享 / 绑定服务
            shared_infos = list(ServiceSharingManager(module).list_all_shared_info())
            bound_services = list(mixed_service_mgr.list_binded(module))

            # 已经启用的增强服务
            bound_service_obj_allocations = self._gen_service_obj_allocations(module, bound_services)
            bound_service_infos = list(bound_service_obj_allocations.values())
            # 补充引用当前模块实例的模块信息
            sharing_ref_mgr = SharingReferencesManager(module)
            for svc_info in bound_service_infos:
                svc_info["ref_modules"] = sharing_ref_mgr.list_related_modules(svc_info["service"])

            # 共享其他模块的增强服务
            shared_service_infos = []
            for shared_info in shared_infos:
                svc = shared_info.service
                ref_svc_allocation = self._gen_service_obj_allocations(shared_info.ref_module, services=[svc])[
                    svc.uuid
                ]
                shared_service_infos.append(
                    {
                        "service": svc,
                        "module": shared_info.module,
                        "ref_module": shared_info.ref_module,
                        "provision_infos": ref_svc_allocation["provision_infos"],
                    }
                )

            # 组合数据
            modules_data.append(
                {
                    "module_name": module.name,
                    "bound_services": bound_service_infos,
                    "shared_services": shared_service_infos,
                }
            )

        # 返回模块数据
        slz = slzs.ServiceListOutputSLZ(modules_data, many=True)
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_200_OK: slzs.UnboundServiceInstanceSLZ(many=True)},
    )
    def list_unbound_attachments(self, request, code):
        """列出未绑定的增强服务实例"""
        result = []
        application = get_object_or_404(Application, code=code)
        for module in application.modules.all():
            for env in module.envs.all():
                # 获取可回收的增强服务实例
                for rel in mixed_service_mgr.list_unbound_instance_rels(engine_app=env.engine_app):
                    instance = rel.get_instance()
                    if not instance:
                        # 如果已经回收了，获取不到 instance，跳过
                        continue

                    instance_data = dict(
                        uuid=rel.db_obj.service_instance_id,
                        config=instance.config,
                        credentials=instance.get_credentials(),
                    )

                    result.append(
                        dict(
                            environment=env.environment,
                            module=module.name,
                            service=mixed_service_mgr.get_or_404(rel.db_obj.service_id),
                            instance=instance_data,
                        )
                    )
        return Response(slzs.UnboundServiceInstanceSLZ(result, many=True).data)

    @atomic
    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_201_CREATED: None},
    )
    def provision_instance(self, request, code, module_name, environment, service_id):
        """分配增强服务实例"""
        application = get_object_or_404(Application, code=code)
        module = get_object_or_404(application.modules.all(), name=module_name)
        env = module.envs.get(environment=environment)
        service = mixed_service_mgr.get_or_404(service_id)

        rel = next(mixed_service_mgr.list_unprovisioned_rels(engine_app=env.engine_app, service=service), None)
        if not rel:
            raise error_codes.CANNOT_PROVISION_INSTANCE.f(_("当前环境不存在未分配的增强服务实例"))

        rel.provision()
        data_after = self._gen_audit_detail(rel=rel)
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.PROVISION_INSTANCE,
            target=OperationTarget.APP,
            app_code=code,
            module_name=module_name,
            environment=environment,
            data_after=data_after,
        )
        return Response(status=status.HTTP_201_CREATED)

    @atomic
    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def unbound_instance(self, request, code, module_name, environment, service_id, instance_id):
        """解绑增强服务实例"""
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
            data_before = self._gen_audit_detail(rel=instance_rel)
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

    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def recycle_unbound_instance(self, request, code, module_name, service_id, instance_id):
        """回收未绑定的增强服务实例"""
        service = mixed_service_mgr.get_or_404(service_id)

        try:
            rel = mixed_service_mgr.get_unbound_instance_rel_by_instance_id(
                service=service,
                service_instance_id=instance_id,
            )
        except SvcAttachmentDoesNotExist:
            raise Http404

        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data={
                "service": ServiceObjOutputSLZ(mixed_service_mgr.get_or_404(rel.db_obj.service_id)).data,
                "instance": ServiceInstanceOutputSLZ(rel.get_instance()).data,
            },
        )
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

    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_200_OK: "credentials in JSON format"},
    )
    def view_credentials(self, request, code, module_name, environment, service_id, instance_id):
        """查看增强服务实例凭据"""

        service = mixed_service_mgr.get_or_404(service_id)

        rel = mixed_service_mgr.get_instance_rel_by_instance_id(service, instance_id)
        if not rel:
            raise Http404

        return Response(rel.get_instance().get_credentials())

    @staticmethod
    def _gen_service_obj_allocations(module: Module, services: List[ServiceObj]) -> Dict[str, Any]:
        """生成服务对象分配信息"""
        svc_allocation_map: Dict[str, Dict[str, Any]] = {
            svc.uuid: {"service": svc, "provision_infos": [], "plans": {}} for svc in services
        }
        for env in module.get_envs():
            rels = mixed_service_mgr.list_all_rels(env.engine_app)
            for rel in rels:
                svc = rel.get_service()
                if svc.uuid not in svc_allocation_map:
                    continue

                alloc = svc_allocation_map[svc.uuid]
                alloc["provision_infos"].append(
                    {
                        "env_name": env.environment,
                        "is_provisioned": rel.is_provisioned(),
                        "instance_uuid": rel.get_instance().uuid if rel.is_provisioned() else None,
                    }
                )
                plan = rel.get_plan()
                alloc["plans"][env.environment] = {
                    "name": plan.name,
                    "description": plan.description,
                }

        return svc_allocation_map

    @staticmethod
    def _gen_audit_detail(rel: EngineAppInstanceRel) -> DataDetail:
        """生成服务实例相关的审计数据"""
        data = {
            "service": ServiceObjOutputSLZ(rel.get_service()).data,
            "instance": ServiceInstanceOutputSLZ(rel.get_instance()).data,
            "plan": PlanObjOutputSLZ(rel.get_plan()).data,
        }

        return DataDetail(type=DataType.RAW_DATA, data=data)
