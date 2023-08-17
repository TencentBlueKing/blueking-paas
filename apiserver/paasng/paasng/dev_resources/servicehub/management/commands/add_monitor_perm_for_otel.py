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
"""Add BK Monitoring space permissions to applications that have enabled the Otel service.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from paasng.accessories.bkmonitorv3.client import make_bk_monitor_client
from paasng.accessories.bkmonitorv3.exceptions import BkMonitorSpaceDoesNotExist
from paasng.accessories.iam.tasks import add_monitoring_space_permission
from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = 'Add BK Monitoring space permissions to apps that have enabled the Otel service.'

    def add_arguments(self, parser):
        parser.add_argument("--region", required=False, type=str, default=settings.DEFAULT_REGION_NAME)
        parser.add_argument("--dry-run", default=False, action="store_true", help="dry run")

    def handle(self, region, dry_run, *args, **options):
        service = mixed_service_mgr.find_by_name('otel', region)
        application_ids = list(Application.objects.all().values_list('id', flat=True))
        # 查询所有以开启 otel 增强服务的应用信息
        service_instances = mixed_service_mgr.get_provisioned_queryset(service, application_ids)
        for ins in service_instances:
            application = ins.module.application
            self.stdout.write(
                self.style.NOTICE(f"app_code: {application.code}, module:{ins.module.name} start adding permissions.")
            )
            if dry_run:
                continue

            # 查询应用对应的空间ID
            cli = make_bk_monitor_client()
            try:
                space_detail = cli.get_space_detail(application.code)
            except BkMonitorSpaceDoesNotExist as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"app_code: {application.code}, module:{ins.module.name} add permissions failed. {e}"
                    )
                )
                continue

            # 同步执行添加监控日志平台应用空间权限的操作
            add_monitoring_space_permission(application.code, application.name, space_detail.bk_space_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"app_code: {application.code}, module:{ins.module.name} add permissions successfully."
                )
            )
