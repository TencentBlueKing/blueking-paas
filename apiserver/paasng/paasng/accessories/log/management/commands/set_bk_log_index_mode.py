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

"""设置指定 App 的日志链路使用「独立索引」或「平台共享索引」

适用场景: App 需要在独立索引和平台共享索引之间互转

执行步骤:
  1. 删除模块下目标模式以外的内置 CustomCollectorConfig 行 (DB), 避免历史残留持续被部署回写
  2. 重跑每个 env 的目标 bk-log setup, 写入目标模式的 ProcessLogQueryConfig / 采集项
  3. 删除集群里仍指向旧模式 data_id 的 BkLogConfig CRD, 避免下次部署前同时存在两组 BkLogConfig

注意: 上游 (蓝鲸日志平台) 的内置采集项可能被其他环境/应用复用, 所以这里不会调用日志平台 API 删除上游采集项,
仅清理本 App 的本地引用与 K8s CRD。切换完成后, 需要重新部署应用让目标模式的 BkLogConfig 下发到集群

Examples:
    # 切到独立索引
    python manage.py set_bk_log_index_mode --app-code app-code-1 --index-mode independent

    # 切到共享索引
    python manage.py set_bk_log_index_mode --app-code app-code-1 --index-mode shared

    # dry-run, 仅打印将要执行的动作
    python manage.py set_bk_log_index_mode --app-code app-code-1 --index-mode shared --dry-run
"""

from typing import Literal

from django.core.management.base import BaseCommand, CommandError
from django.db.transaction import atomic

from paas_wl.bk_app.monitoring.bklog.kres_entities import bklog_config_kmodel
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.accessories.log.models import CustomCollectorConfig
from paasng.accessories.log.shim.setup_bklog import build_custom_collector_config_name, setup_default_bk_log_model
from paasng.accessories.log.shim.setup_bklog_shared import SHARED_INDEX_NAMES, setup_shared_bk_log_model
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.models import Module

IndexMode = Literal["independent", "shared"]
INDEX_MODES: tuple[IndexMode, ...] = ("independent", "shared")
BUILTIN_LOG_TYPES = ("json", "stdout")


class Command(BaseCommand):
    help = "Set a specific app to use per-module independent or platform shared bk-log index path."

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", required=True, help="应用 Code")
        parser.add_argument(
            "--index-mode",
            dest="index_mode",
            choices=INDEX_MODES,
            default="independent",
            help="目标索引模式: independent=应用模块独立索引, shared=平台共享索引。默认 independent, 兼容旧命令行为",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            default=False,
            help="仅打印将要执行的动作, 不实际写 DB / 调用 K8s API",
        )

    def handle(self, app_code: str, index_mode: IndexMode, dry_run: bool, *args, **options):
        try:
            application = Application.objects.get(code=app_code)
        except Application.DoesNotExist:
            raise CommandError(f"Application not found: code={app_code}")

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(f"{prefix}set Application<{app_code}> bk-log index mode to {index_mode}")

        for module in application.modules.all():
            envs = list(module.get_envs())
            stale_db_collector_names = _get_stale_db_collector_names(module, index_mode)
            stale_crd_collector_names = _get_stale_crd_collector_names(module, index_mode, stale_db_collector_names)
            if dry_run:
                self._print_dry_run_actions(
                    application, module, envs, index_mode, stale_db_collector_names, stale_crd_collector_names, prefix
                )
                continue

            with atomic():
                deleted_rows = _delete_stale_collector_rows(module, index_mode)
                if deleted_rows:
                    self.stdout.write(
                        f"deleted {deleted_rows} stale CustomCollectorConfig row(s) for "
                        f"Application<{app_code}> Module<{module.name}>: {', '.join(stale_db_collector_names)}"
                    )

                for env in envs:
                    _setup_target_bk_log_model(env, index_mode)
                    self.stdout.write(
                        f"re-setup {index_mode} bk-log model for "
                        f"Application<{app_code}> Module<{module.name}> Env<{env.environment}>"
                    )

            for env in envs:
                deleted_crds = _delete_stale_bklog_crds(env, stale_crd_collector_names)
                if deleted_crds:
                    self.stdout.write(
                        f"deleted {deleted_crds} stale BkLogConfig CRD(s) in cluster for "
                        f"Application<{app_code}> Module<{module.name}> Env<{env.environment}>"
                    )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    "Set bk-log index mode done. Please trigger a redeploy of the application to apply the new "
                    "BkLogConfig CRDs."
                )
            )

    def _print_dry_run_actions(
        self,
        application: Application,
        module: Module,
        envs: list[ModuleEnvironment],
        index_mode: IndexMode,
        stale_db_collector_names: list[str],
        stale_crd_collector_names: list[str],
        prefix: str,
    ):
        if stale_db_collector_names:
            self.stdout.write(
                f"{prefix}would delete {len(stale_db_collector_names)} stale CustomCollectorConfig row(s) for "
                f"Application<{application.code}> Module<{module.name}>: {', '.join(stale_db_collector_names)}"
            )

        crd_count = len(stale_crd_collector_names)

        for env in envs:
            self.stdout.write(
                f"{prefix}would re-setup {index_mode} bk-log model for "
                f"Application<{application.code}> Module<{module.name}> Env<{env.environment}>"
            )
            self.stdout.write(
                f"{prefix}would delete up to {crd_count} stale BkLogConfig CRD(s) in cluster for "
                f"Application<{application.code}> Module<{module.name}> Env<{env.environment}>"
            )


def _get_stale_db_collector_names(module: Module, target_mode: IndexMode) -> list[str]:
    """获取目标模式以外的内置采集项名称"""
    qs = CustomCollectorConfig.objects.filter(module=module, is_builtin=True)
    if target_mode == "independent":
        qs = qs.filter(name_en__in=SHARED_INDEX_NAMES)
    else:
        qs = qs.exclude(name_en__in=SHARED_INDEX_NAMES)
    return list(qs.values_list("name_en", flat=True))


def _get_stale_crd_collector_names(
    module: Module, target_mode: IndexMode, stale_db_collector_names: list[str]
) -> list[str]:
    """获取需要尝试清理的旧模式 BkLogConfig 对应采集项名称"""
    if target_mode == "independent":
        known_stale_names = SHARED_INDEX_NAMES
    else:
        known_stale_names = {
            build_custom_collector_config_name(module, type=log_type) for log_type in BUILTIN_LOG_TYPES
        }
    return sorted(set(stale_db_collector_names) | known_stale_names)


def _delete_stale_collector_rows(module: Module, target_mode: IndexMode) -> int:
    """物理删除模块下目标模式以外的内置 CustomCollectorConfig 行"""
    qs = CustomCollectorConfig.objects.filter(module=module, is_builtin=True)
    if target_mode == "independent":
        qs = qs.filter(name_en__in=SHARED_INDEX_NAMES)
    else:
        qs = qs.exclude(name_en__in=SHARED_INDEX_NAMES)
    deleted, _ = qs.delete()
    return deleted


def _setup_target_bk_log_model(env: ModuleEnvironment, target_mode: IndexMode):
    """按目标模式初始化蓝鲸日志平台采集方案的数据库模型"""
    if target_mode == "independent":
        return setup_default_bk_log_model(env)
    return setup_shared_bk_log_model(env)


def _delete_stale_bklog_crds(env: ModuleEnvironment, stale_collector_names: list[str]) -> int:
    """删除集群中由旧模式采集项下发的 BkLogConfig CRD"""
    deleted = 0
    for name_en in stale_collector_names:
        crd_name = _to_bklog_crd_name(name_en)
        try:
            existed = bklog_config_kmodel.get(app=env.wl_app, name=crd_name)
        except AppEntityNotFound:
            continue
        bklog_config_kmodel.delete(existed)
        deleted += 1
    return deleted


def _to_bklog_crd_name(collector_config_name: str) -> str:
    """转换自定义采集项名称为 BkLogConfig CRD 名称"""
    return collector_config_name.replace("_", "-")
