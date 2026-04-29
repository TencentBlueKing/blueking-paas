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

"""把指定 App 的日志链路从「平台共享索引」切回「独立索引」

适用场景: App 希望使用独立索引

执行步骤:
  1. 删除模块下命中共享模板的 CustomCollectorConfig 行 (DB), 避免历史残留持续被部署回写
  2. 重跑每个 env 的独立 bk-log setup, 写入独立的 ProcessLogQueryConfig / 采集项
  3. 删除集群里仍指向共享 data_id 的 BkLogConfig CRD, 避免下次部署前同时存在两组 BkLogConfig

注意: 上游 (蓝鲸日志平台) 的共享采集项是按租户__共用__的, 所以这里不会调用日志平台 API 删除上游采集项,
仅清理本 App 的本地引用与 K8s CRD。

Examples:
    # 实际执行迁移
    python manage.py migrate_app_to_independent_bk_log_index --app-code app-code-1

    # dry-run, 仅打印将要执行的动作
    python manage.py migrate_app_to_independent_bk_log_index --app-code app-code-1 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.transaction import atomic

from paas_wl.bk_app.monitoring.bklog.kres_entities import bklog_config_kmodel
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.accessories.log.models import CustomCollectorConfig
from paasng.accessories.log.shim.setup_bklog import setup_default_bk_log_model
from paasng.accessories.log.shim.setup_bklog_shared import SHARED_INDEX_NAMES
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.models import Module


class Command(BaseCommand):
    help = "Switch a specific app to keep using per-module independent bk-log index path."

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", required=True, help="应用 Code")
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            default=False,
            help="仅打印将要执行的动作, 不实际写 DB / 调用 K8s API",
        )

    def handle(self, app_code: str, dry_run: bool, *args, **options):
        try:
            application = Application.objects.get(code=app_code)
        except Application.DoesNotExist:
            raise CommandError(f"Application not found: code={app_code}")

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(f"{prefix}migrate Application<{app_code}> to independent bk-log index path")

        for module in application.modules.all():
            envs = list(module.get_envs())
            if dry_run:
                self._print_dry_run_actions(application, module, envs, prefix)
                continue

            with atomic():
                deleted_rows = _delete_shared_collector_rows(module)
                if deleted_rows:
                    self.stdout.write(
                        f"deleted {deleted_rows} shared CustomCollectorConfig row(s) for "
                        f"Application<{app_code}> Module<{module.name}>"
                    )

                for env in envs:
                    setup_default_bk_log_model(env)
                    self.stdout.write(
                        f"re-setup independent bk-log model for "
                        f"Application<{app_code}> Module<{module.name}> Env<{env.environment}>"
                    )

            for env in envs:
                deleted_crds = _delete_shared_bklog_crds(env)
                if deleted_crds:
                    self.stdout.write(
                        f"deleted {deleted_crds} shared BkLogConfig CRD(s) in cluster for "
                        f"Application<{app_code}> Module<{module.name}> Env<{env.environment}>"
                    )

        if not dry_run:
            self.stdout.write(
                "Migration done. Please trigger a redeploy of the application to apply the new BkLogConfig CRDs."
            )

    def _print_dry_run_actions(
        self, application: Application, module: Module, envs: list[ModuleEnvironment], prefix: str
    ):
        shared_count = CustomCollectorConfig.objects.filter(module=module, is_builtin=True).count()
        if shared_count:
            self.stdout.write(
                f"{prefix}would delete {shared_count} shared CustomCollectorConfig row(s) for "
                f"Application<{application.code}> Module<{module.name}>"
            )

        for env in envs:
            self.stdout.write(
                f"{prefix}would re-setup independent bk-log model for "
                f"Application<{application.code}> Module<{module.name}> Env<{env.environment}>"
            )
            self.stdout.write(
                f"{prefix}would delete up to {len(SHARED_INDEX_NAMES)} shared BkLogConfig CRD(s) in cluster for "
                f"Application<{application.code}> Module<{module.name}> Env<{env.environment}>"
            )


def _delete_shared_collector_rows(module: Module) -> int:
    """物理删除模块下命中共享采集项 name_en 的 CustomCollectorConfig 行"""
    deleted, _ = CustomCollectorConfig.objects.filter(
        module=module, is_builtin=True, name_en__in=SHARED_INDEX_NAMES
    ).delete()
    return deleted


def _delete_shared_bklog_crds(env: ModuleEnvironment) -> int:
    """删除集群中由共享采集项下发的 BkLogConfig CRD"""
    deleted = 0
    for name_en in SHARED_INDEX_NAMES:
        crd_name = name_en.replace("_", "-")
        try:
            existed = bklog_config_kmodel.get(app=env.wl_app, name=crd_name)
        except AppEntityNotFound:
            continue
        bklog_config_kmodel.delete(existed)
        deleted += 1
    return deleted
