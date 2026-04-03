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
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.db.utils import ProgrammingError
from django.utils.timezone import get_default_timezone

from paasng.accessories.log.models import TenantLogConfig
from paasng.core.tenant.user import get_init_tenant_id

logger = logging.getLogger(__name__)


def init_default_tenant_log_config(**kwargs):
    """初始化默认租户的日志配置

    兼容策略：
    - 将全局配置 settings.BKLOG_CONFIG 转换为默认租户的 TenantLogConfig
    - 只在不存在时创建，避免覆盖已有配置
    """
    # 检查表是否存在
    try:
        TenantLogConfig.objects.exists()
    except ProgrammingError:
        logger.info("TenantLogConfig table not ready, skip initialization")
        return

    default_tenant_id = get_init_tenant_id()

    if TenantLogConfig.objects.filter(tenant_id=default_tenant_id).exists():
        return

    # 创建默认租户配置
    bklog_config = settings.BKLOG_CONFIG
    try:
        with transaction.atomic():
            # timezone 默认值和 django 的 TIME_ZONE 保持一致
            timezone = bklog_config.get("TIME_ZONE")
            if timezone is None:
                default_tz = get_default_timezone()
                timezone = int(default_tz.utcoffset(datetime.now()).total_seconds() // 60 // 60)

            try:
                config = TenantLogConfig.objects.create(
                    tenant_id=default_tenant_id,
                    storage_cluster_id=bklog_config["STORAGE_CLUSTER_ID"],
                    retention=bklog_config["RETENTION"],
                    es_shards=bklog_config["ES_SHARDS"],
                    storage_replicas=bklog_config["STORAGE_REPLICAS"],
                    time_zone=timezone,
                )
            except KeyError as e:
                logger.exception("Missing required BKLOG_CONFIG key: %s", e.args[0])
                return
            logger.info(
                "Created TenantLogConfig for default tenant %s: storage_cluster_id=%s",
                default_tenant_id,
                config.storage_cluster_id,
            )
    except Exception:
        logger.exception("Failed to create TenantLogConfig")
