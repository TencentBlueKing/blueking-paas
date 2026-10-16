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

from celery.signals import worker_process_init
from django.apps import AppConfig

from paasng.settings.utils import is_in_celery_worker

from .setup import setup_by_settings


class TracingConfig(AppConfig):
    name = "paas_wl.workloads.tracing"

    def ready(self):
        # prefork 父进程不能在这里建 OTel 的 gRPC exporter。exporter 会拉起后台导出线程，
        # fork 时若该线程正在调用 gRPC，子进程会继承半初始化状态并段错误退出。
        # worker 改到 worker_process_init，等每个子进程 fork 完成后再初始化。
        if is_in_celery_worker():
            return

        setup_by_settings()


@worker_process_init.connect(weak=False)
def setup_otel_trace_after_worker_fork(*args, **kwargs):
    """在 prefork 子进程里初始化 OTel。"""

    # 该信号在每个子进程 fork 完成之后触发。此时再建 exporter，线程只活在本子进程里。
    setup_by_settings()
