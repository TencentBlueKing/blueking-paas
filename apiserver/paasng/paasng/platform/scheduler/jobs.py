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
from contextlib import contextmanager

from apscheduler.schedulers.background import BackgroundScheduler as Scheduler
from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.manager import get_db_properties, mixed_service_mgr
from paasng.accessories.servicehub.models import (
    DefaultPolicyCreationRecord,
    ServiceBindingPolicy,
    ServiceBindingPrecedencePolicy,
)
from paasng.accessories.servicehub.remote.collector import fetch_all_remote_services
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.core.core.storages.redisdb import get_default_redis
from paasng.core.tenant.user import get_init_tenant_id

logger = logging.getLogger(__name__)
scheduler = Scheduler()


@scheduler.scheduled_job("interval", minutes=settings.REMOTE_SERVICES_UPDATE_INTERVAL_MINUTES)
def update_remote_services():
    """Update remote services periodically"""
    remote_store = get_remote_store()
    logger.debug("Start updating remote services...")
    for ret in fetch_all_remote_services():
        remote_store.bulk_upsert(ret.data, meta_info=ret.meta_info, source_config=ret.config)


@contextmanager
def redis_lock(lock_key: str, timeout: int = 300):
    """Redis 分布式锁上下文管理器，确保跨进程的原子操作

    :param lock_key: 锁的唯一标识键，建议遵循命名规范如 lock:<业务场景>
    :param timeout: 锁自动释放的超时时间（秒），预防死锁
    """
    redis_conn = get_default_redis()
    lock = redis_conn.lock(
        name=lock_key,
        timeout=timeout,
        blocking_timeout=0,  # 非阻塞模式，立即返回
        thread_local=False,
    )

    acquired = lock.acquire()
    try:
        if acquired:
            logger.debug("Successfully acquired lock for %s", lock_key)
        else:
            logger.debug("Failed to acquire lock for %s", lock_key)
        yield acquired
    finally:
        # 只有当前进程持有的锁才释放
        if acquired:
            lock.release()
            logger.debug("Released lock for %s", lock_key)


def _handel_single_service_default_policy(service, default_tenant_id):
    """初始化默认租户下的增强服务绑定策略

    :param service: 增强服务实例
    :param default_tenant_id: 默认租户 ID

    说明：
    - 仅初始化默认租户方案（默认租户下一般是通过 fixture 等在后台配置的增强服务方案 ）
    - 其他租户是在页面上配置增强服务方案，所以绑定策略也应该在页面上配置，不应该由后台默认初始化

    NOTE: 后续可以提供一键初始化某个租户下所有增强服务的脚本或者 API，比如在 yaml 里面配置好所有增强服务的方案后执行一个命令就能完成所有增强服务的初始化动作
    """
    with transaction.atomic():
        # 如果已经存在默认策略创建记录，则跳过
        # 使用 select_for_update 加锁防止并发问题
        if DefaultPolicyCreationRecord.objects.filter(service_id=service.uuid).exists():
            logger.debug("Default policy for service(%s) already exists, skip init", service.name)
            return

        has_existing_policy = (
            ServiceBindingPolicy.objects.filter(service_id=service.uuid).exists()
            or ServiceBindingPrecedencePolicy.objects.filter(service_id=service.uuid).exists()
        )
        service_type = get_db_properties(service).col_service_type
        # 如果已经存在分别策略，则创建初始化记录并跳过初始化
        if has_existing_policy:
            _, created = DefaultPolicyCreationRecord.objects.get_or_create(
                service_id=service.uuid,
                defaults={
                    "service_type": service_type,
                    "finished_at": now(),
                },
            )
            if created:
                logger.info("Created default policy record for service(%s) with existing policies", service.name)
            return

        try:
            plans = service.get_plans_by_tenant_id(default_tenant_id)
            if not plans:
                logger.warning("No plans available for service(%s) under tenant(%s)", service.name, default_tenant_id)
                return

            SvcBindingPolicyManager(service, default_tenant_id).set_uniform(plans=[p.uuid for p in plans])
            # 添加初始化记录，避免重复初始化
            DefaultPolicyCreationRecord.objects.get_or_create(
                service_id=service.uuid,
                defaults={
                    "service_type": service_type,
                    "finished_at": now(),
                },
            )
            logger.info("Successfully initialized default policy for service(%s)", service.name)
        except Exception:
            logger.exception("Init default policy for service(%s) error", service.name)


@scheduler.scheduled_job("interval", minutes=settings.REMOTE_SERVICES_UPDATE_INTERVAL_MINUTES)
def init_service_default_policy_job():
    """初始化服务默认策略的定时任务

    功能特性：
    - 使用分布式锁确保集群环境下的单实例执行
    - 自动适配多租户模式配置
    """
    # 使用分布式锁确保只有一个进程执行初始化
    lock_key = "lock:init_service_default_policy"
    with redis_lock(lock_key) as acquired:
        if not acquired:
            logger.info("Another instance is handling service policy initialization, skip.")
            return

        logger.info("Starting service policy initialization process.")

        default_tenant_id = get_init_tenant_id()
        for service in mixed_service_mgr.list():
            _handel_single_service_default_policy(service, default_tenant_id)

        logger.info("Service policy initialization completed.")
