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
import logging

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone

from paasng.engine.constants import JobStatus
from paasng.engine.models.deployment import Deployment
from paasng.engine.models.offline import OfflineOperation
from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.utils.datetime import get_time_delta

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "refresh operation(Deployment & Offline) pending status"

    def add_arguments(self, parser):
        parser.add_argument('--dry_run', action='store_true')
        parser.add_argument('--timeout', type=str, default="1h")

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.timeout = options['timeout']

        # 从脚本执行时往前算过期时间点
        self.now = timezone.now()

        deploy_operations = self.get_timeout_pending_operations(Deployment)
        offline_operations = self.get_timeout_pending_operations(OfflineOperation)
        overall_operations = self.get_timeout_pending_operations(ModuleEnvironmentOperations)

        self.update_pending_status(deploy_operations)
        self.update_pending_status(offline_operations)
        self.update_pending_status(overall_operations, err_detail=False)

    def get_timeout_pending_operations(self, model_class) -> QuerySet:
        end_time = self.now - get_time_delta(self.timeout)
        return model_class.objects.filter(status=JobStatus.PENDING, updated__lt=end_time)

    def update_pending_status(self, operations: QuerySet, err_detail: bool = True):
        if not operations:
            return

        if self.dry_run:
            logger.info("DRY-RUN: \n")

        model_class = type(operations[0]).__name__
        pending_count = operations.count()
        logger.info("going to update type<%s> count<%s>", model_class, pending_count)

        try:
            update_param = {"status": JobStatus.FAILED, "updated": self.now}
            # ModuleEnvironmentOperations 是没有 err_detail 的
            if err_detail:
                update_param.update({"err_detail": f"executing more than {self.timeout}, regarding as failed by PaaS"})

            if not self.dry_run:
                operations.update(**update_param)

            logger.info("update type<%s> done", model_class)
        except Exception:
            logger.error("update type<%s> failed", model_class)
