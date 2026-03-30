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

import json
from contextlib import contextmanager
from typing import Generator

from blue_krill.models.fields import EncryptField
from django.db import models, transaction
from django.utils import timezone
from paas_service.models import UuidAuditedModel

from .constants import InstanceStatus


class InstanceBill(UuidAuditedModel):
    """实例单据，保存申请上下文，方便重入"""

    engine_app_name = models.CharField("应用名称", max_length=64)
    instance_status = models.CharField("实例状态", max_length=16)
    context = EncryptField(verbose_name="上下文", default="{}")
    locked_at = models.DateTimeField("锁定时间", null=True)

    def mark_error(self, message: str):
        """标记单据为错误状态，保存错误信息到上下文"""
        context = self.get_context()
        context["error"] = message
        self.instance_status = InstanceStatus.ERROR
        self.set_context(context)
        self.save(update_fields=["instance_status", "context"])

    def get_context(self) -> dict:
        return json.loads(self.context or "{}")

    def set_context(self, context: dict):
        self.context = json.dumps(context)

    @contextmanager
    def log_context(self) -> Generator[dict, None, None]:
        context = self.get_context()
        try:
            yield context
        finally:
            self.set_context(context)
            self.save()

    def acquire_lock(self) -> bool:
        """尝试获取锁（原子操作），成功返回 True，已被锁定返回 False"""
        with transaction.atomic():
            ins = InstanceBill.objects.select_for_update().get(uuid=self.uuid)
            if ins.locked_at:
                return False
            ins.locked_at = timezone.now()
            ins.save(update_fields=["locked_at"])
        self.refresh_from_db()
        return True

    def release_lock(self):
        """释放锁"""
        self.locked_at = None
        self.save(update_fields=["locked_at"])

    @contextmanager
    def lock_for_creation(self) -> Generator[bool, None, None]:
        """尝试获取创建锁的上下文管理器

        yield True 表示成功获取锁（调用方应执行创建逻辑），异常时自动释放；
        yield False 表示已被其他进程锁定（调用方应等待就绪）。
        """
        acquired = self.acquire_lock()
        try:
            yield acquired
        finally:
            if acquired:
                self.release_lock()
