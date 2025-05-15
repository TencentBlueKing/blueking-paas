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

from paasng.accessories.servicehub.constants import LEGACY_PLAN_ID, ServiceType
from paasng.accessories.servicehub.exceptions import (
    SvcAttachmentDoesNotExist,
)
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import ServiceModuleAttachment, SharedServiceAttachment
from paasng.accessories.servicehub.services import EngineAppInstanceRel
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

    def _get_module_services(self, module) -> Dict[str, Dict[str, Any]]:
        """获取模块下的增强服务"""
        # 获取该模块下所有服务记录，包括直接服务和共享服务
        services_map = {}

        ## 获取直接服务
        attachments = ServiceModuleAttachment.objects.filter(module=module).select_related("service")
        for attachment in attachments:
            service = attachment.service
            services_map[service.pk] = {
                "service_id": str(service.pk),
                "service_name": service.name,
                "config": service.config,
                "environment": [],
                "is_shared": False,
                "shared_from": None,
            }
        ## 获取共享服务
        shared_attachments = SharedServiceAttachment.objects.filter(
            module=module, service_type=ServiceType.LOCAL
        ).exclude(ref_attachment_pk=None)

        if not shared_attachments:
            return services_map

        ## 获取引用附件信息
        ref_attachment_ids = [sa.ref_attachment_pk for sa in shared_attachments]
        ref_attachments = ServiceModuleAttachment.objects.filter(id__in=ref_attachment_ids).select_related(
            "service", "module"
        )

        # 创建ID到附件的映射，减少循环查找
        ref_map = {ref.pk: ref for ref in ref_attachments}

        # 4. 处理共享服务
        for shared in shared_attachments:
            ref = ref_map.get(shared.ref_attachment_pk)
            if not ref:
                continue

            service = ref.service
            # 避免和直接服务重复
            if service.pk in services_map:
                continue

            services_map[service.pk] = {
                "service_id": str(service.pk),
                "service_name": service.name,
                "config": service.config,
                "environment": [],
                "is_shared": True,
                "shared_from": ref.module.name,
            }

        return services_map

    def _fill_environment_info(self, module, services_map) -> None:
        """填充环境信息"""

        name_to_pk = {data["service_name"]: pk for pk, data in services_map.items()}

        ## 获取环境部署状态
        for env in module.envs.all():
            engine_app = env.engine_app
            services_rels = mixed_service_mgr.list_all_rels(engine_app=engine_app)
            for rel in services_rels:
                service = rel.get_service()
                if service.name in name_to_pk:
                    pk = name_to_pk[service.name]
                    services_map[pk]["environment"].append(
                        {"env_name": env.environment, "is_deploy_instance": rel.is_provisioned()}
                    )

    @swagger_auto_schema(
        tags=["plat_mgt.applications.services"],
        responses={status.HTTP_200_OK: slzs.ApplicationAddonServicesListOutputSLZ(many=True)},
    )
    def list(self, request, app_code):
        """获取增强服务列表"""

        application = get_object_or_404(Application, code=app_code)
        modules_data = []

        for module in application.modules.all():
            # 准备模块数据结构
            module_data = {
                "module_name": module.name,
                "addons_service": [],
            }

            # 获取模块下的增强服务
            services_map = self._get_module_services(module)

            # 填充环境信息
            self._fill_environment_info(module, services_map)

            ## 将服务列表添加到模块数据中
            service_list = sorted(services_map.values(), key=lambda x: x["service_name"])
            module_data["addons_service"] = service_list
            modules_data.append(module_data)

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
