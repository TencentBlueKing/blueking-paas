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
from paas_service.models import ServiceInstance

from svc_bk_repo.monitoring.metrics import auto_expand_counter
from svc_bk_repo.monitoring.models import AutoExpandEvent
from svc_bk_repo.shared.scheduler import db_distributed_lock, scheduler
from svc_bk_repo.vendor.actions import extend_quota
from svc_bk_repo.vendor.exceptions import ExtendQuotaMaxSizeExceeded, ExtendQuotaUsageTooLow, NoNeedToExtendQuota
from svc_bk_repo.vendor.helper import get_repo_manager
from svc_bk_repo.vendor.render import humanize_bytes

logger = logging.getLogger(__name__)


@scheduler.scheduled_job("interval", minutes=settings.BKREPO_COLLECT_INTERVAL_MINUTES)
def auto_extend_bkrepo_quota():
    """根据全局配置自动扩容所有实例的 bkrepo 仓库配额"""
    if not settings.BKREPO_AUTO_EXPAND_ENABLED:
        logger.info("BKRepo auto-expand is globally disabled, skip.")
        return

    threshold = settings.BKREPO_AUTO_EXPAND_USAGE_THRESHOLD
    with db_distributed_lock("auto_extend_bkrepo_quota") as acquired:
        if not acquired:
            return

        logger.info("Starting auto-extend bkrepo quota.")
        for instance in ServiceInstance.objects.all():
            manager = get_repo_manager(instance.plan_id)
            credentials = instance.get_credentials()
            private_bucket = credentials["private_bucket"]
            public_bucket = credentials["public_bucket"]

            for bucket_name in (private_bucket, public_bucket):
                try:
                    old_quota = manager.get_repo_quota(bucket_name)
                    new_size = extend_quota(
                        manager,
                        bucket=bucket_name,
                        extra_size_bytes=settings.EXTEND_CONFIG_EXTRA_SIZE_BYTES,
                        max_allowed_bytes=settings.EXTEND_CONFIG_MAX_SIZE_ALLOWED,
                        required_usage_rate=threshold,
                    )
                    AutoExpandEvent.objects.create(
                        instance=instance,
                        repo_name=bucket_name,
                        old_size=int(old_quota.max_size),
                        new_size=new_size,
                        step_size=settings.EXTEND_CONFIG_EXTRA_SIZE_BYTES,
                    )
                    auto_expand_counter.labels(
                        service_id=str(instance.service_id),
                        instance_id=str(instance.id),
                        repo_name=bucket_name,
                    ).inc()
                    logger.info(
                        "Auto-extended quota for instance=%s bucket=%s: %s -> %s (+%s)",
                        instance.uuid,
                        bucket_name,
                        humanize_bytes(int(old_quota.max_size)),
                        humanize_bytes(new_size),
                        humanize_bytes(settings.EXTEND_CONFIG_EXTRA_SIZE_BYTES),
                    )
                except NoNeedToExtendQuota:
                    logger.debug("Bucket=%s has no quota limit, skip auto-extend.", bucket_name)
                except ExtendQuotaUsageTooLow:
                    logger.debug("Bucket=%s usage below threshold, skip auto-extend.", bucket_name)
                except ExtendQuotaMaxSizeExceeded:
                    logger.warning(
                        "Bucket=%s already at max allowed size (%s), cannot auto-extend.",
                        bucket_name,
                        humanize_bytes(settings.EXTEND_CONFIG_MAX_SIZE_ALLOWED),
                    )
                except Exception:
                    logger.exception("Unknown error while auto-extending bucket=%s", bucket_name)

        logger.info("Auto-extend bkrepo quota finished.")
