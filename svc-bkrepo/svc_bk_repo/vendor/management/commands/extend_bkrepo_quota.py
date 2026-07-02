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


from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from paas_service.models import ServiceInstance
from paas_service.utils import get_paas_app_info

from svc_bk_repo.vendor.actions import extend_quota
from svc_bk_repo.vendor.helper import BKGenericRepoManager
from svc_bk_repo.vendor.render import humanize_bytes


class Command(BaseCommand):
    help = "为指定的 bkrepo 实例扩容仓库配额"

    def add_arguments(self, parser):
        parser.add_argument("instance_id", type=str, help="ServiceInstance 的 UUID")
        parser.add_argument(
            "--bucket_type",
            type=str,
            choices=["private", "public"],
            default="private",
            help="扩容的仓库类型 (默认: private)",
        )
        parser.add_argument(
            "--extra_size",
            type=int,
            default=settings.EXTEND_CONFIG_EXTRA_SIZE_BYTES,
            help="扩容增量, 单位 GB (默认: 1)",
        )
        parser.add_argument(
            "--max_allowed",
            type=int,
            default=settings.EXTEND_CONFIG_MAX_SIZE_ALLOWED,
            help="扩容上限, 单位 GB (默认: 10)",
        )

    def handle(self, instance_id: str, bucket_type: str, extra_size: int, max_allowed: int, *args, **options):
        # GB -> bytes
        # 参考: vendor.render.ABBREVS
        #   ABBREVS = ((1 << 50, "PB"), (1 << 40, "TB"), (1 << 30, "GB"), (1 << 20, "MB"), (1 << 10, "KB"), (1, "bytes"))
        extra_size_bytes = extra_size * (2**30)
        max_allowed_bytes = max_allowed * (2**30)

        try:
            instance = ServiceInstance.objects.get(uuid=instance_id)
        except ServiceInstance.DoesNotExist:
            raise CommandError(f"ServiceInstance 不存在: {instance_id}")

        plan_config = instance.plan.get_config()
        manager = BKGenericRepoManager(**plan_config)

        credentials = instance.get_credentials()
        if bucket_type == "private":
            bucket = credentials["private_bucket"]
        else:
            bucket = credentials["public_bucket"]

        # 展示业务侧信息, 方便定位
        try:
            app_info = get_paas_app_info(instance)
            app_code = app_info["app_code"]
            model_name = app_info["model_name"]
            environment = app_info["environment"]
            self.stdout.write(
                f"正在为实例 {instance_id} (关联应用: {app_code} / {model_name} / {environment}) 扩容 {bucket_type} 仓库配额..."
            )
        except Exception:  # noqa: BLE001
            self.stdout.write(f"正在为实例 {instance_id} 扩容 {bucket_type} 仓库配额...")

        quota_before = manager.get_repo_quota(bucket)
        self.stdout.write(
            f"当前容量: {humanize_bytes(quota_before.used)} / {humanize_bytes(quota_before.max_size)} ({quota_before.quota_used_rate:.1f}%)"
        )

        new_max_size_bytes = extend_quota(
            manager=manager,
            bucket=bucket,
            extra_size_bytes=extra_size_bytes,
            max_allowed_bytes=max_allowed_bytes,
            # Command 管理员命令, 不校验限制使用率
            required_usage_rate=None,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"扩容成功: {humanize_bytes(new_max_size_bytes)} (增加了 {humanize_bytes(max_allowed_bytes)})"
            )
        )
