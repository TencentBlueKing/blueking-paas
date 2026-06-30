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

from django.db.models.signals import post_save
from django.dispatch import receiver

from svc_bk_repo.monitoring.metrics import auto_expand_counter
from svc_bk_repo.monitoring.models import AutoExpandEvent

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AutoExpandEvent)
def report_auto_expand_metric(sender, instance, created, **kwargs):
    """自动扩容事件写入 DB 后, 上报 Prometheus Counter"""

    if not created:
        return
    auto_expand_counter.labels(
        service_id=str(instance.instance.service_id),
        instance_id=str(instance.instance_id),
        repo_name=instance.repo_name,
    ).inc()
    logger.debug("Auto-expand metric reported: instance=%s repo=%s", instance.instance_id, instance.repo_name)
