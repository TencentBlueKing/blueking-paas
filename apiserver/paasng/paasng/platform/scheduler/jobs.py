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

from paasng.accessories.servicehub.remote.collector import fetch_all_remote_services
from paasng.accessories.servicehub.remote.store import get_remote_store

logger = logging.getLogger(__name__)
scheduler = Scheduler()


@scheduler.scheduled_job("interval", minutes=settings.REMOTE_SERVICES_UPDATE_INTERVAL_MINUTES)
def update_remote_services():
    """Update remote services periodically"""
    remote_store = get_remote_store()
    logger.debug("Start updating remote services...")
    for ret in fetch_all_remote_services():
        remote_store.bulk_upsert(ret.data, meta_info=ret.meta_info, source_config=ret.config)
