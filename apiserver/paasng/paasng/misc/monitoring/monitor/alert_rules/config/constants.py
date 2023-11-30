# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.platform.applications.constants import AppEnvironment

from .entities import AlertCode

RUN_ENVS = AppEnvironment.get_values()

RABBITMQ_SERVICE_NAME = settings.RABBITMQ_MONITOR_CONF.get("service_name", "rabbitmq")


DEFAULT_RULE_CONFIGS = {
    AlertCode.HIGH_CPU_USAGE.value: {
        "display_name": _("CPU 使用率过高"),
        "metric_label_names": ["namespace", "bcs_cluster_id"],
        "threshold_expr": ">= 0.8",  # 使用率 80%
    },
    AlertCode.HIGH_MEM_USAGE.value: {
        "display_name": _("内存使用率过高"),
        "metric_label_names": ["namespace", "bcs_cluster_id"],
        "threshold_expr": ">= 0.95",  # 使用率 95%
    },
    AlertCode.POD_RESTART.value: {
        "display_name": _("异常重启"),
        "metric_label_names": ["namespace", "bcs_cluster_id"],
        "threshold_expr": ">= 1",  # 出现至少 1 次
    },
    AlertCode.OOM_KILLED.value: {
        "display_name": _("OOMKilled 退出"),
        "metric_label_names": ["namespace", "bcs_cluster_id"],
        "threshold_expr": ">= 1",  # 出现至少 1 次
    },
    AlertCode.HIGH_RABBITMQ_QUEUE_MESSAGES.value: {
        "display_name": _("队列消息数过多"),
        "metric_label_names": ["vhost"],
        "threshold_expr": ">= 2000",  # 超过 2000 条
    },
}
