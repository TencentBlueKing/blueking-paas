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

from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessServicesFlag
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


def upsert_process_service_flag(m: Module, implicit_needed: bool):
    """upsert process service flag by app module

    :param m: app module
    :param implicit_needed: 是否隐式需要 process services 配置
    """
    for env in m.get_envs():
        ProcessServicesFlag.objects.update_or_create(
            app_environment=env,
            defaults={"implicit_needed": implicit_needed, "tenant_id": m.tenant_id},
        )
