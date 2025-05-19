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

from typing import Any, Dict

from django.db.transaction import atomic
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.servicehub.constants import LEGACY_PLAN_ID
from paasng.accessories.servicehub.exceptions import (
    SvcAttachmentDoesNotExist,
)
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.services import EngineAppInstanceRel
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_mgt.applications.serializers import services as slzs
from paasng.platform.applications.models import Application
from paasng.utils.error_codes import error_codes


class ApplicationAddonServicesViewSet(viewsets.ViewSet):
    """平台管理 - 应用增强服务"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @staticmethod
    def _gen_service_data_detail(rel: EngineAppInstanceRel) -> DataDetail:
        return DataDetail(
            type=DataType.RAW_DATA,
            data={
                "service": slzs.ApplicationAddonServicesObjSLZ(rel.get_service()).data,
                "instance": slzs.ApplicationAddonServicesInstanceSLZ(rel.get_instance()).data,
                "plan": slzs.ApplicationAddonServicesPlanSLZ(rel.get_plan()).data,
            },
        )

    def _get_module_services_with_env_info(self, module) -> Dict[str, Dict[str, Any]]:
        """获取模块下的增强服务及其环境信息"""
        services_map: Dict[str, Any] = {}

        ## 获取直接服务
        for service in mixed_service_mgr.list_binded(module):
            services_map[service.uuid] = {
                "service_uuid": str(service.uuid),
                "service_name": service.name,
                "config": [],
                "is_shared": False,
                "shared_from": None,
            }
        ## 获取共享服务
        for shared_info in ServiceSharingManager(module).list_all_shared_info():
            service = shared_info.service
            if service.uuid not in services_map:
                services_map[service.uuid] = {
                    "service_uuid": str(service.uuid),
                    "service_name": service.name,
                    "config": [],
                    "is_shared": True,
                    "shared_from": shared_info.ref_module.name,
                }

        name_to_uuid = {data["service_name"]: uuid for uuid, data in services_map.items()}

        # 填充环境信息
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_all_rels(engine_app=env.engine_app):
                service = rel.get_service()
                service_uuid = name_to_uuid.get(service.name)
                if service_uuid:
                    services_map[service_uuid]["config"].append(
                        {
                            "env_name": env.environment,
                            "is_deploy_instance": rel.is_provisioned(),
                            "plan_name": rel.get_plan().name,
                            "plan_description": rel.get_plan().description,
                        }
                    )

        return services_map

    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_200_OK: slzs.ApplicationAddonServicesListOutputSLZ(many=True)},
    )
    def list(self, request, app_code):
        """获取增强服务列表"""

        application = get_object_or_404(Application, code=app_code)
        modules_data = []

        for module in application.modules.all():
            # 获取模块的服务及环境信息
            services_map = self._get_module_services_with_env_info(module)

            ## 将服务列表添加到模块数据中
            service_list = sorted(services_map.values(), key=lambda x: x["service_name"])
            modules_data.append({"module_name": module.name, "addons_service": service_list})

        # 返回模块数据
        slz = slzs.ApplicationAddonServicesListOutputSLZ(modules_data, many=True)
        return Response(slz.data)

    @atomic
    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_201_CREATED: None},
    )
    def assign_instance(self, request, app_code, module_name, env_name, service_id):
        """分配增强服务实例"""
        application = get_object_or_404(Application, code=app_code)
        module = get_object_or_404(application.modules.all(), name=module_name)
        env = module.envs.get(environment=env_name)
        service = mixed_service_mgr.get_or_404(service_id)

        rel = next(mixed_service_mgr.list_unprovisioned_rels(engine_app=env.engine_app, service=service), None)
        if not rel:
            raise error_codes.CANNOT_PROVISION_INSTANCE.f(_("当前环境不存在未分配的增强服务实例"))

        rel.provision()
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.PROVISION_INSTANCE,
            target=OperationTarget.APP,
            app_code=app_code,
            module_name=module,
            environment=env,
            data_after=self._gen_service_data_detail(rel),
        )
        return Response(status=status.HTTP_201_CREATED)

    @atomic
    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def delete_instance(self, request, app_code, module_name, env_name, service_id, instance_id):
        """删除增强服务实例"""
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
                app_code=app_code,
                module_name=module_name,
                data_before=data_before,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def view_credentials(self, request, app_code, module_name, env_name, service_id, instance_id):
        """查看增强服务实例凭据"""
        service = mixed_service_mgr.get_or_404(service_id)

        try:
            instance_rel = mixed_service_mgr.get_instance_rel_by_instance_id(service, instance_id)
        except SvcAttachmentDoesNotExist:
            raise Http404

        instance = instance_rel.get_instance()
        return Response({"result": instance.credentials})
