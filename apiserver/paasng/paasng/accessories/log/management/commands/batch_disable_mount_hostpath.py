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

import datetime

import arrow
from django.core.management.base import BaseCommand, CommandError
from django.db.models import QuerySet

from paas_wl.bk_app.applications.models import Config
from paas_wl.bk_app.monitoring.bklog.constants import WLAPP_NAME_ANNO_KEY
from paas_wl.bk_app.monitoring.bklog.kres_entities import bklog_config_kmodel
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.applications.constants import AppFeatureFlag as AppFeatureFlagConst
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application, ModuleEnvironment


class Command(BaseCommand):
    help = "A command to batch disable mount host path"

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", help="应用 Code", default="", required=False)
        parser.add_argument(
            "--cluster", dest="cluster_name", help="处理指定集群内的所有 BkApp", default="", required=False
        )
        parser.add_argument(
            "--all-clusters",
            dest="all_clusters",
            action="store_true",
            default=False,
            help="处理所有应用集群的所有 BkApp",
        )
        parser.add_argument("--no-dry-run", dest="dry_run", help="dry run", action="store_false")
        parser.add_argument(
            "--edge-disable",
            dest="edge_disable",
            help="是否忽略应用维度的条件, 当环境符合时直接禁用宿主机挂载点",
            action="store_true",
            default=False,
        )

    def handle(
        self, app_code: str, cluster_name: str, all_clusters: bool, edge_disable: bool, dry_run: bool, *args, **options
    ):
        style_func = self.style.SUCCESS if not dry_run else self.style.NOTICE
        qs = self.validate_params(app_code, cluster_name, all_clusters)
        for application in qs:
            self.process_single_application(application, edge_disable, dry_run, style_func)

    def process_single_application(self, application: Application, edge_disable: bool, dry_run: bool, style_func):
        can_use_bklog = True
        pending_latest_config = []

        for module in application.modules.all():
            for env in module.envs.all():  # type: ModuleEnvironment
                env_can_use_bklog = self.check_env_status(env)

                if env_can_use_bklog:
                    if not dry_run:
                        # 日志平台采集配置已下发大于 14 天, 可停用平台日志采集链路
                        # Note: 需等待用户下次触发配置时，才会真正生效
                        wl_app = env.wl_app
                        # warning: latest_config 是 property, 必须拿出来后才能修改
                        latest_config = wl_app.latest_config
                        latest_config.mount_log_to_host = False
                        if edge_disable:
                            latest_config.save(update_fields=["mount_log_to_host", "updated"])
                        else:
                            pending_latest_config.append(latest_config)

                    self.stdout.write(
                        "disable hostpath log collector for "
                        f"Application<{application.code}> "
                        f"Module<{module.name}>"
                        f"Env<{env.environment}>",
                        style_func=style_func,
                    )
                # 必须所有环境都满足条件, 才将整个应用的日志查询链路切换到 BK-LOG
                can_use_bklog = can_use_bklog and env_can_use_bklog

        if can_use_bklog:
            if not dry_run:
                application.feature_flag.set_feature(AppFeatureFlagConst.ENABLE_BK_LOG_COLLECTOR, True)
                for cfg in pending_latest_config:
                    cfg.save(update_fields=["mount_log_to_host", "updated"])

            self.stdout.write(
                f"switch log query to bk-log index for Application<{application.code}>",
                style_func=style_func,
            )

    def validate_params(self, app_code, cluster_name, all_clusters) -> QuerySet:
        """Validate all parameter combinations, return the filtered Application QuerySet"""
        if cluster_name != "":
            if app_code:
                raise CommandError("'cluster_name' and 'app_code' can't be used together.")
            # 查询集群下的所有 engine app
            # django 不支持跨库关联查询, 必须用 list 强制转换
            all_engine_app_ids = list(Config.objects.filter(cluster=cluster_name).values_list("app__uuid", flat=True))
            # 通过 engine app id 反查 Application
            return Application.objects.filter(envs__engine_app_id__in=all_engine_app_ids)
        elif all_clusters:
            return Application.objects.exclude(type=ApplicationType.ENGINELESS_APP)
        else:
            return Application.objects.filter(code=app_code)

    def check_env_status(self, env: ModuleEnvironment) -> bool:
        cluster = EnvClusterService(env).get_cluster()
        # 其中一个环境的集群不支持 BK-LOG 采集器, 不能使用 BK-LOG 查询链路
        if not cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR):
            return False

        wl_app = env.wl_app
        one_of_bklogconfig = next(
            iter(bklog_config_kmodel.list_by_app(app=env.wl_app, labels={WLAPP_NAME_ANNO_KEY: wl_app.name})),
            None,
        )
        # 该环境未下发 BK-LOG 配置, 不能使用 BK-LOG 查询链路
        if not one_of_bklogconfig:
            return False

        # 如果该环境的 BK-LOG 配置下发时间小于 14 天, 切换日志查询链路有可能丢失日志, 故暂不能切换 BK-LOG 查询链路
        creation_timestamp = arrow.get(one_of_bklogconfig._kube_data["metadata"]["creationTimestamp"])
        return arrow.now() - creation_timestamp > datetime.timedelta(days=14)
