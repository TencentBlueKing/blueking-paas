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

"""沿用 loaddata 的事务和加密字段，只在内存中替换方案配置。"""

import json
from collections.abc import Mapping

from django.core.management.base import CommandError
from django.core.management.commands.loaddata import Command as LoadDataCommand

from svc_mysql.settings.kms import _decrypt_envelope, is_kms_enabled


class KMSFixtureError(CommandError):
    """只携带安全的方案标识和字段名。"""


class Command(LoadDataCommand):
    help = "从 fixture 导入服务，并从 KMS 信封导入完整方案配置"

    def handle(self, *fixture_labels, **options):
        self.plan_configs = None
        if not is_kms_enabled():
            return super().handle(*fixture_labels, **options)

        # 各服务的现有信封新增 service_plans，以方案 UUID 为键保存完整配置。
        # 不生成明文文件；正常 ORM 保存会通过 Plan.config 的 EncryptField 加密落库。
        self.plan_configs = _decrypt_envelope().get("service_plans")
        if not isinstance(self.plan_configs, Mapping):
            raise KMSFixtureError("KMS requires a service_plans object")
        try:
            return super().handle(*fixture_labels, **options)
        except KMSFixtureError:
            raise
        except Exception:
            # Django 的 fixture/数据库异常可能包含字段值；不能将这些值输出到 Job 日志。
            raise CommandError("Unable to import KMS fixtures; transaction rolled back") from None

    def save_obj(self, obj):
        if self.plan_configs is not None and obj.object._meta.label_lower == "paas_service.plan":
            plan_id = str(obj.object.pk)
            config = self.plan_configs.get(plan_id)
            if not isinstance(config, Mapping) or not config:
                raise KMSFixtureError(f"KMS requires complete configuration for service_plans.{plan_id}")
            self._check_passwords(config, plan_id)
            obj.object.config = json.dumps(config, ensure_ascii=False)
        return super().save_obj(obj)

    @staticmethod
    def _check_passwords(config, plan_id):
        # MySQL/RabbitMQ 多服务器配置的每个服务器都需要密码；单服务器与 bkrepo 使用顶层密码。
        entries = config.get("servers") or config.get("clusters") or [config]
        if not isinstance(entries, list) or any(
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("password"), str)
            or not entry["password"].strip()
            for entry in entries
        ):
            raise KMSFixtureError(f"KMS requires passwords for service_plans.{plan_id}")
