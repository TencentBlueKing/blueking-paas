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

"""取消将应用的日志文件挂载到宿主机上，一般在将应用的日志查询链路切换到 BK-LOG 14 天后执行。

Q1: 为什么需要禁用宿主机挂载点？
A1: 日志平台的采集机制是在每个 pod 中采集日志，不禁用挂载会导致应用有多个 pod 时日志被重复采集。

Q2: 为什么不在应用的日志采集链路切换到 BK-LOG 时立即禁用挂载
A2: 切换到 BK-LOG 是整个应用级别生效，很多应用需要先在测试环境验证，这个时候一般都需要在 ELK、BK-LOG 这两个链路都采集日志，所以事后再手动关闭挂载比较合适。
    大多数应用对日志重复采集不敏感，而是对丢失日志敏感，所以延迟取消挂载比较合适。

Examples:

    # 应用所有环境的 bklog 日志采集下发都超过了 14 天，才取消应用所有环境的挂载
    python manage.py batch_disable_mount_hostpath --app-code app-code-1

    # 应用任意环境符合条件（bklog 日志采集下发超过 1 天）即禁用该环境挂载
    python manage.py batch_disable_mount_hostpath --app-code app-code-1  --days 1 --edger-disable

    # 关闭指定集群下应用的挂载
    python manage.py batch_disable_mount_hostpath --cluster cluster-name1

    # 关闭所有集群下的应用挂载
    python manage.py batch_disable_mount_hostpath --all-clusters
"""

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
        parser.add_argument(
            "--edger-disable",
            dest="edger_disable",
            help="当任意环境符合条件时直接禁用该环境的挂载，无需等待所有环境就绪",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            dest="days",
            help="日志采集配置生效天数阈值（默认 14 天）",
        )
        parser.add_argument("--no-dry-run", dest="dry_run", help="dry run", action="store_false")

    def handle(
        self,
        app_code: str,
        cluster_name: str,
        all_clusters: bool,
        edger_disable: bool,
        days: int,
        dry_run: bool,
        *args,
        **options,
    ):
        if cluster_name != "" and app_code:
            raise CommandError("'cluster_name' and 'app_code' can't be used together.")

        style_func = self.style.SUCCESS if not dry_run else self.style.NOTICE
        qs = self.get_target_applications(app_code, cluster_name, all_clusters)
        for application in qs:
            self.process_single_application(application, edger_disable, days, dry_run, style_func)

    def process_single_application(
        self, application: Application, edger_disable: bool, days: int, dry_run: bool, style_func
    ):
        """处理单个应用的挂载配置

        :param application: 需要处理的应用
        :param edger_disable: True-环境级处理：任意环境符合条件即禁用该环境挂载 / False-应用级处理：所有环境都符合条件才禁用全部挂载
        :param days: 日志采集配置生效天数阈值
        :param dry_run: 调试模式，不实际保存修改
        :param style_func: 输出样式函数
        """
        pending_latest_config = []
        all_envs_valid = True

        for module in application.modules.all():
            for env in module.envs.all():
                if not self.check_env_using_bklog(env, days):
                    all_envs_valid = False
                    continue

                # 调试模式下只记录日志不修改配置
                if not dry_run:
                    # 日志平台采集配置已下发大于 14 天, 可停用平台日志采集链路
                    # Note: 需等待用户下次触发配置时，才会真正生效
                    wl_app = env.wl_app
                    # warning: latest_config 是 property, 必须拿出来后才能修改
                    latest_config = wl_app.latest_config
                    latest_config.mount_log_to_host = False
                    # 忽略应用维度的条件, 当前环境符合时直接禁用宿主机挂载
                    if edger_disable:
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

        # 所有环境都有效时更新应用特性，并禁用应用所有环境的挂载
        if all_envs_valid:
            if not dry_run:
                application.feature_flag.set_feature(AppFeatureFlagConst.ENABLE_BK_LOG_COLLECTOR, True)
                for cfg in pending_latest_config:
                    cfg.save(update_fields=["mount_log_to_host", "updated"])

            self.stdout.write(
                f"switch log query to bk-log index for Application<{application.code}>",
                style_func=style_func,
            )

    def get_target_applications(self, app_code: str, cluster_name: str, all_clusters: bool) -> QuerySet[Application]:
        """根据参数组合获取目标应用集合

        :param app_code: 应用 ID
        :param cluster_name: 集群名称
        :param all_clusters: 是否获取所有集群下的应用
        """
        if cluster_name != "":
            # 查询集群下的所有 engine app
            # django 不支持跨库关联查询, 必须用 list 强制转换
            all_engine_app_ids = list(Config.objects.filter(cluster=cluster_name).values_list("app__uuid", flat=True))
            # 通过 engine app id 反查 Application
            return Application.objects.filter(envs__engine_app_id__in=all_engine_app_ids).distinct()
        elif all_clusters:
            return Application.objects.exclude(type=ApplicationType.ENGINELESS_APP)
        else:
            return Application.objects.filter(code=app_code)

    def check_env_using_bklog(self, env: ModuleEnvironment, days: int) -> bool:
        """检查环境是已完全使用 BK-LOG 查询日志

        :param days: 日志采集配置生效天数阈值
        """
        cluster = EnvClusterService(env).get_cluster()
        # 环境对应集群的不支持 BK-LOG 日志采集, 不能使用 BK-LOG 查询链路
        if not cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR):
            return False

        wl_app = env.wl_app
        has_any_bklogconfig = next(
            iter(bklog_config_kmodel.list_by_app(app=wl_app, labels={WLAPP_NAME_ANNO_KEY: wl_app.name})),
            None,
        )
        # 该环境未下发 BK-LOG 配置, 不能使用 BK-LOG 查询链路
        if not has_any_bklogconfig:
            return False

        # 如果该环境的 BK-LOG 配置下发时间小于 14 天, 切换日志查询链路有可能丢失日志, 故暂不能切换 BK-LOG 查询链路
        creation_timestamp = arrow.get(has_any_bklogconfig._kube_data["metadata"]["creationTimestamp"])
        return arrow.now() - creation_timestamp > datetime.timedelta(days=days)
