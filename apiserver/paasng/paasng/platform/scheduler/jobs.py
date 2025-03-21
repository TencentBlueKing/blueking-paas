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

import logging

from apscheduler.schedulers.background import BackgroundScheduler as Scheduler
from django.conf import settings

from paasng.accessories.servicehub.binding_policy.manager import ServiceBindingPolicyManager
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import (
    ServiceBindingPolicy,
    ServiceBindingPolicyAutoBindRecord,
    ServiceBindingPrecedencePolicy,
)
from paasng.accessories.servicehub.remote.collector import fetch_all_remote_services
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID

logger = logging.getLogger(__name__)
scheduler = Scheduler()


@scheduler.scheduled_job("interval", minutes=settings.REMOTE_SERVICES_UPDATE_INTERVAL_MINUTES)
def update_remote_services():
    """Update remote services periodically"""
    remote_store = get_remote_store()
    logger.debug("Start updating remote services...")
    for ret in fetch_all_remote_services():
        remote_store.bulk_upsert(ret.data, meta_info=ret.meta_info, source_config=ret.config)


@scheduler.scheduled_job("interval", minutes=settings.REMOTE_SERVICES_UPDATE_INTERVAL_MINUTES)
def init_service_binding_policy():
    """
    初始化默认租户下的增强服务绑定策略

    说明：
    - 仅初始化默认租户方案（默认租户下一般是通过 fixture 等在后台配置的增强服务方案 ）
    - 其他租户是在页面上配置增强服务方案，所以绑定策略也应该在页面上配置，不应该由后台默认初始化

    NOTE: 后续可以提供一键初始化某个租户下所有增强服务的脚本或者 API，比如在 yaml 里面配置好所有增强服务的方案后执行一个命令就能完成所有增强服务的初始化动作
    """
    default_tenant_id = OP_TYPE_TENANT_ID if settings.ENABLE_MULTI_TENANT_MODE else DEFAULT_TENANT_ID

    for service in mixed_service_mgr.list():
        # 增强服务已经绑定过，或者已经有绑定策略则不再自动绑定
        if (
            ServiceBindingPolicyAutoBindRecord.objects.filter(service_id=service.uuid).exists()
            or ServiceBindingPolicy.objects.filter(service_id=service.uuid).exists()
            or ServiceBindingPrecedencePolicy.objects.filter(service_id=service.uuid).exists()
        ):
            logger.debug("Service binding policy for service(%s) already exists, skip init", service.name)
            continue
        try:
            plans = service.get_plans_by_tenant_id(default_tenant_id)
            if not plans:
                logger.warning(
                    "No service plans found for service(%s) under tenant(%s), skip init",
                    service.name,
                    default_tenant_id,
                )
                continue

            ServiceBindingPolicyManager(service, default_tenant_id).set_static(plans)
            # 添加自动绑定记录，避免重复初始化
            ServiceBindingPolicyAutoBindRecord.objects.create(service_id=service.uuid)
            logger.info("Init service binding policy for service(%s) success", service.name)
        except Exception:
            logger.exception("Init service binding policy for service(%s) error", service.name)
