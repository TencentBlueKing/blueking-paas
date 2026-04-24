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

"""把指定 App 的日志查询/采集链路从 "平台共享索引" 切回 "按 module 独立建项" 链路

适用场景: 平台级开关 ENABLE_SHARED_BK_LOG_INDEX=True, 但需要个别 App 保留独立索引

执行内容:
  1. 给该 App 置 AppFeatureFlag.USE_INDEPENDENT_BK_LOG_INDEX=True
     (这是持久标记, 防止后续日志页查询/插件中心查询/celery 任务等热路径把配置覆盖回共享)
  2. 遍历该 App 的所有 module/env, 重跑 setup_env_log_model
     (有标记保护, 此时会路由到独立分支, 重写 ProcessLogQueryConfig/ElasticSearchConfig 指向独立索引,
      并通过 setup_bk_log_custom_collector 在 bk-log 创建/复用独立采集项)
  3. 把模块下旧的 "平台共享" CustomCollectorConfig 行置 is_enabled=False
     (避免下次部署 AppLogConfigController.create_or_patch 同时下发独立 + 共享两组 BkLogConfig CR,
      造成日志双采集)

不在范围:
  - 不会主动清理 K8s 里旧的共享 BkLogConfig CR; 建议命令成功后触发该 App 一次重新部署再人工清理

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
                # 先重跑 setup_env_log_model: flag 已置位, 走独立分支, 写入独立的 CustomCollectorConfig 行
                # 然后再禁用旧的共享行, 顺序不能反 (反过来会被 setup 的 update_or_create 重新启用)
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
        """dry-run 模式打印将要执行的动作, 不修改任何数据"""
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

            shared_names = _shared_collector_name_set(module.tenant_id)
            shared_qs = CustomCollectorConfig.objects.filter(module=module, name_en__in=shared_names, is_enabled=True)
            if shared_qs.exists():
                self.stdout.write(
                    f"{prefix}would disable {shared_qs.count()} shared CustomCollectorConfig row(s) for "
                    f"Application<{application.code}> Module<{module.name}>",
                    style_func=style_func,
                )

    def _disable_shared_collector_rows(self, module) -> int:
        """把模块下旧的共享采集项行置 is_enabled=False, 返回受影响行数"""
        shared_names = _shared_collector_name_set(module.tenant_id)
        return CustomCollectorConfig.objects.filter(module=module, name_en__in=shared_names, is_enabled=True).update(
            is_enabled=False
        )


def _shared_collector_name_set(tenant_id: str) -> set:
    """渲染该租户的共享采集项 name_en 集合 (json + stdout)"""
    return {
        PLATFORM_INDEX_NAME_JSON_TEMPLATE.format(tenant_id=tenant_id),
        PLATFORM_INDEX_NAME_STDOUT_TEMPLATE.format(tenant_id=tenant_id),
    }
