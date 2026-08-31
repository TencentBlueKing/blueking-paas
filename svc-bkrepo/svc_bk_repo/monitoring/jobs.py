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
import math

from django.conf import settings
from paas_service.models import ServiceInstance

from svc_bk_repo.monitoring.models import RepoQuotaStatistics
from svc_bk_repo.shared.scheduler import scheduler
from svc_bk_repo.vendor.helper import get_repo_manager

logger = logging.getLogger(__name__)


@scheduler.scheduled_job("interval", minutes=settings.BKREPO_COLLECT_INTERVAL_MINUTES)
def update_bkrepo_quota_statistics():
    """Update bkrepo quota statistics periodically"""
    logger.info("Starting update bkrepo quota.")
    for instance in ServiceInstance.objects.all():
        manager = get_repo_manager(instance)

        credentials = instance.get_credentials()
        private_bucket = credentials["private_bucket"]
        public_bucket = credentials["public_bucket"]
        private_quota = manager.get_repo_quota(private_bucket)
        public_quota = manager.get_repo_quota(public_bucket)

        # 无限制容量跳过记录用量 metrics
        if not math.isinf(private_quota.max_size):
            RepoQuotaStatistics.objects.update_or_create(
                instance=instance,
                repo_name=private_bucket,
                defaults={"max_size": private_quota.max_size, "used": private_quota.used},
            )
        else:
            logger.info("Private repo %s has unlimited quota, skip update", private_bucket)

        if not math.isinf(public_quota.max_size):
            RepoQuotaStatistics.objects.update_or_create(
                instance=instance,
                repo_name=public_bucket,
                defaults={"max_size": public_quota.max_size, "used": public_quota.used},
            )
        else:
            logger.info("Public repo %s has unlimited quota, skip update", public_bucket)

    logger.info("bkrepo quota updated.")
