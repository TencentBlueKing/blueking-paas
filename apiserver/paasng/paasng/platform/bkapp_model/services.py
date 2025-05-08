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

from paas_wl.bk_app.cnative.specs.constants import DEFAULT_PROCESS_NAME
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities.proc_service import ExposedType, ProcService
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module


def check_replicas_manually_scaled(m: Module) -> bool:
    """check if replicas has been manually scaled by web form"""
    process_names = ModuleProcessSpec.objects.filter(module=m).values_list("name", flat=True)

    if not process_names:
        return False

    # NOTE: 页面手动扩缩容会修改 spec.env_overlay.replicas 的管理者为 web_form, 因此只需要检查 f_overlay_replicas 字段
    replicas_fields = []
    for proc_name in process_names:
        for env_name in AppEnvName:
            replicas_fields.append(fieldmgr.f_overlay_replicas(proc_name, env_name))

    managers = fieldmgr.MultiFieldsManager(m).get(replicas_fields)
    return fieldmgr.FieldMgrName.WEB_FORM in managers.values()


def upsert_proc_svc_by_spec_version(m: Module, spec_version: AppSpecVersion | None):
    """upsert process services base on spec version defined in app_desc.yaml file.

    When spec version lower than 3 (or when only a Procfile exists), default process services must be upserted.
    Otherwise, this function performs no operation.
    """
    # 由于低于 3 版本的 app_desc.yaml/Procfile 不支持显式配置 process services, 因此由平台创建
    if spec_version in [None, AppSpecVersion.VER_1, AppSpecVersion.VER_2]:
        proc_specs = ModuleProcessSpec.objects.filter(module=m)

        for proc_spec in proc_specs:
            proc_svc = ProcService(
                name=proc_spec.name,
                target_port=settings.CONTAINER_PORT,
                protocol="TCP",
                port=80,
            )
            if proc_spec.name == DEFAULT_PROCESS_NAME:
                proc_svc.exposed_type = ExposedType()

            proc_spec.services = [proc_svc]

        if proc_specs:
            ModuleProcessSpec.objects.bulk_update(proc_specs, ["services"])
