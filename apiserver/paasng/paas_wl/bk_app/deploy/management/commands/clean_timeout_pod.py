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

import arrow
from django.core.management.base import BaseCommand
from django.utils import timezone

from paas_wl.bk_app.deploy.app_res.controllers import BuildHandler
from paas_wl.infras.resources.base.base import get_all_cluster_names, get_client_by_cluster_name
from paas_wl.infras.resources.base.kres import KPod
from paasng.platform.engine.configurations.building import BUILD_DEBUG_TIMEOUT


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--dry-run", dest="dry_run", help="dry run", action="store_true")
        parser.add_argument(
            "--timeout", help="slug pod timeout(default is 3600s), please use seconds", type=int, default=60 * 60
        )

    def handle(self, dry_run, timeout, *args, **options):
        now = timezone.now()

        for cluster_name in get_all_cluster_names():
            client = get_client_by_cluster_name(cluster_name)
            pods = KPod(client).ops_batch.list(labels={"category": "slug-builder"})
            timeout_count = 0
            # normally, there is only one slug instance
            for pod in pods.items:
                if self._is_debug_pod(pod):
                    # 检查 debug Pod 的调试窗口是否已过期
                    if not BuildHandler.is_debug_window_available(pod, BUILD_DEBUG_TIMEOUT):
                        self._delete_pod(client, pod, dry_run, reason="debug window expired")
                        timeout_count += 1
                else:
                    # 非 debug Pod: 基于 creationTimestamp 判断
                    timedelta = now - arrow.get(pod.metadata.creationTimestamp).datetime
                    if timedelta.total_seconds() > timeout:
                        self._delete_pod(client, pod, dry_run, reason=f"running > {timeout}s")
                        timeout_count += 1

            self.stdout.write(f"{cluster_name} has {timeout_count} timeout pods, cleaned\n")

    def _is_debug_pod(self, pod) -> bool:
        """检查 Pod 是否为构建调试 Pod (label build-debug=true)."""
        return (pod.metadata.labels or {}).get("build-debug") == "true"

    def _delete_pod(self, client, pod, dry_run: bool, reason: str):
        """删除 Pod, dry_run 模式仅打印日志."""
        self.stdout.write(f"{pod.metadata.name} is expired ({reason}), going to delete it")
        if dry_run:
            self.stdout.write("DRY-RUN: cleaned !")
            return
        KPod(client).delete(name=pod.metadata.name, namespace=pod.metadata.namespace)
        self.stdout.write("cleaned !")
