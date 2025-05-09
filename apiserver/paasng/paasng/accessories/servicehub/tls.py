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

from typing import Iterable

from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.services import EngineAppInstanceRel
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.platform.applications.models import ModuleEnvironment


def is_rel_tls_enabled(rel: EngineAppInstanceRel) -> bool:
    """判断指定的增强服务实例是否启用了 TLS"""
    cfg = rel.get_instance().config
    return cfg and cfg.get("provider_name") and cfg.get("enable_tls")


def list_provisioned_tls_enabled_rels(env: ModuleEnvironment) -> Iterable[EngineAppInstanceRel]:
    """获取指定环境的已经分配 & 启用 TLS 证书的增强服务实例引用"""

    # 绑定的增强服务
    for service in mixed_service_mgr.list_binded(env.module):
        for rel in mixed_service_mgr.list_provisioned_rels(env.engine_app, service=service):
            if is_rel_tls_enabled(rel):
                yield rel

    # 共享的增强服务
    for shared_info in ServiceSharingManager(env.module).list_all_shared_info():
        # 找到引用的模块环境
        ref_module = env.application.get_module(shared_info.ref_module.name)
        ref_env = ref_module.get_envs(env.environment)
        for rel in mixed_service_mgr.list_provisioned_rels(ref_env.engine_app, service=shared_info.service):
            if is_rel_tls_enabled(rel):
                yield rel
