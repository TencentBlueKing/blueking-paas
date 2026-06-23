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

import logging

from django.conf import settings

from svc_bk_repo.monitoring.models import RepoQuotaStatistics
from svc_bk_repo.shared.scheduler import scheduler
from svc_bk_repo.vendor.actions import extend_quota
from svc_bk_repo.vendor.exceptions import ExtendQuotaMaxSizeExceeded, ExtendQuotaUsageTooLow, NoNeedToExtendQuota
from svc_bk_repo.vendor.helper import BKGenericRepoManager, get_repo_manager

logger = logging.getLogger(__name__)


@scheduler.scheduled_job("interval", minutes=settings.BKREPO_AUTO_EXPAND_CHECK_INTERVAL_MINUTES)
def auto_expand_check():
    """定时任务: 检查所有实例的自动扩容条件, 满足则触发扩容"""
    logger.info("Starting auto-expand check.")

    for stat in RepoQuotaStatistics.objects.select_related("instance").all():
        try:
            manager = get_repo_manager(stat.instance.plan_id)
            _try_auto_expand(stat, manager)
        except Exception:
            logger.exception("Auto expand check failed for %s (instance=%s)", stat.repo_name, stat.instance.uuid)

    logger.info("Auto-expand check finished.")


def _try_auto_expand(stat: RepoQuotaStatistics, manager: BKGenericRepoManager):
    """基于已采集的统计数据判断是否自动扩容, 并在满足条件时触发扩容"""
    bucket_type = "private" if stat.repo_name == stat.instance.get_credentials()["private_bucket"] else "public"
    config = stat.instance.config.get("auto_expand", {}).get(bucket_type)
    if not config or not config["enabled"]:
        return
    if stat.quota_used_rate < config["threshold"]:
        return

    # max_size 为 None 时表示未设置配额, 无需扩容
    if stat.max_size is None:
        logger.warning("Auto expand skip: %s has no quota limit", stat.repo_name)
        return
    # 已达到最大允许值, 不能自动扩容
    if stat.max_size >= settings.EXTEND_CONFIG_MAX_SIZE_ALLOWED:
        logger.warning("Auto expand skip: %s already at max allowed size", stat.repo_name)
        return

    try:
        new_size = extend_quota(
            manager,
            bucket=stat.repo_name,
            extra_size_bytes=settings.EXTEND_CONFIG_EXTRA_SIZE_BYTES,
            max_allowed_bytes=settings.EXTEND_CONFIG_MAX_SIZE_ALLOWED,
            required_usage_rate=config["threshold"],
        )
    except (ExtendQuotaUsageTooLow, NoNeedToExtendQuota):
        logger.info("Auto expand skipped for %s: real-time check says no need", stat.repo_name)
        return
    except ExtendQuotaMaxSizeExceeded:
        logger.info("Auto expand skipped for %s: real-time check says usage too low", stat.repo_name)
        return

    # 扩容成功后同步更新统计记录的 max_size, 避免因旧数据导致下个周期重复触发
    stat.max_size = new_size
    stat.save(update_fields=["max_size"])

    logger.info("Auto expanded %s (instance=%s) -> %s bytes", stat.repo_name, stat.instance.uuid, new_size)
