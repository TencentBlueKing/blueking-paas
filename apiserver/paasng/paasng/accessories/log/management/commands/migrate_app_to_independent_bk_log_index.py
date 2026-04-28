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

"""把指定 App 的日志链路从「平台共享索引」切回「按 module 独立建项」

适用场景: ENABLE_SHARED_BK_LOG_INDEX=True 时, 需要个别 App 保留独立索引

执行三步:
  1. 给 App 置 USE_INDEPENDENT_BK_LOG_INDEX=True, 防止后续热路径把配置回写为共享
  2. 重跑每个 env 的 setup_env_log_model, 写入独立的 ProcessLogQueryConfig / 采集项
  3. 把模块下共享采集项的 CustomCollectorConfig 行禁用, 避免部署时同时下发两组 BkLogConfig CR

注意: 不会清理 K8s 里残留的共享 BkLogConfig CR, 建议执行后触发一次重新部署

Examples:
    # dry-run, 仅打印将要执行的动作
    python manage.py migrate_app_to_independent_bk_log_index --app-code app-code-1

    # 实际生效
    python manage.py migrate_app_to_independent_bk_log_index --app-code app-code-1 --no-dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.transaction import atomic

from paasng.accessories.log.models import CustomCollectorConfig
from paasng.accessories.log.shim import setup_env_log_model
from paasng.infras.bk_log.constatns import (
    PLATFORM_INDEX_NAME_JSON_TEMPLATE,
    PLATFORM_INDEX_NAME_STDOUT_TEMPLATE,
)
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module


class Command(BaseCommand):
    help = "Switch a specific app to keep using per-module independent bk-log index path."

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", required=True, help="应用 Code")
        parser.add_argument(
            "--no-dry-run",
            dest="dry_run",
            action="store_false",
            default=True,
            help="实际执行迁移(默认 dry-run, 仅打印)",
        )

    def handle(self, app_code: str, dry_run: bool, *args, **options):
        try:
            application = Application.objects.get(code=app_code)
        except Application.DoesNotExist:
            raise CommandError(f"Application not found: code={app_code}")

        style_func = self.style.NOTICE if dry_run else self.style.SUCCESS
        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(
            f"{prefix}migrate Application<{app_code}> to independent bk-log index path",
            style_func=style_func,
        )

        if dry_run:
            self._print_actions(application, prefix, style_func)
            return

        with atomic():
            application.feature_flag.set_feature(AppFeatureFlag.USE_INDEPENDENT_BK_LOG_INDEX, True)
            self.stdout.write(
                f"set feature flag USE_INDEPENDENT_BK_LOG_INDEX=True for Application<{app_code}>",
                style_func=style_func,
            )

            for module in application.modules.all():
                # 顺序不能反: 先重跑 setup 写独立采集项, 再禁用共享行;
                # 反过来 setup 的 update_or_create 会把刚禁用的共享行重新启用
                for env in module.get_envs():
                    setup_env_log_model(env)
                    self.stdout.write(
                        f"re-setup independent bk-log model for "
                        f"Application<{app_code}> Module<{module.name}> Env<{env.environment}>",
                        style_func=style_func,
                    )

                disabled = self._disable_shared_collector_rows(module)
                if disabled:
                    self.stdout.write(
                        f"disabled {disabled} shared CustomCollectorConfig row(s) for "
                        f"Application<{app_code}> Module<{module.name}>",
                        style_func=style_func,
                    )

        self.stdout.write(
            "Migration done. Please trigger a redeploy of the application to apply BkLogConfig CR changes; "
            "stale shared BkLogConfig CRs in cluster need manual cleanup if any.",
            style_func=style_func,
        )

    def _print_actions(self, application: Application, prefix: str, style_func):
        """dry-run 模式仅打印将要执行的动作, 不触达 DB / 外部 API"""
        self.stdout.write(
            f"{prefix}would set feature flag USE_INDEPENDENT_BK_LOG_INDEX=True for Application<{application.code}>",
            style_func=style_func,
        )
        for module in application.modules.all():
            for env in module.get_envs():
                self.stdout.write(
                    f"{prefix}would re-setup independent bk-log model for "
                    f"Application<{application.code}> Module<{module.name}> Env<{env.environment}>",
                    style_func=style_func,
                )

            shared_qs = _query_shared_collector_rows(module)
            if shared_qs.exists():
                self.stdout.write(
                    f"{prefix}would disable {shared_qs.count()} shared CustomCollectorConfig row(s) for "
                    f"Application<{application.code}> Module<{module.name}>",
                    style_func=style_func,
                )

    def _disable_shared_collector_rows(self, module: Module) -> int:
        """把模块下共享采集项的 enabled 行置为 False, 返回受影响行数"""
        return _query_shared_collector_rows(module).update(is_enabled=False)


def _query_shared_collector_rows(module: Module):
    """模块下命中共享采集项 name_en 模板 (json + stdout) 且仍 enabled 的 CustomCollectorConfig 查询集"""
    shared_names = {
        PLATFORM_INDEX_NAME_JSON_TEMPLATE.format(tenant_id=module.tenant_id),
        PLATFORM_INDEX_NAME_STDOUT_TEMPLATE.format(tenant_id=module.tenant_id),
    }
    return CustomCollectorConfig.objects.filter(module=module, name_en__in=shared_names, is_enabled=True)
