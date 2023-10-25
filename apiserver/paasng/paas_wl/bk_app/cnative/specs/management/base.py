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
from django.core.management.base import BaseCommand, CommandError
from django.db.models import QuerySet

from paas_wl.bk_app.applications.models import Config
from paas_wl.infras.cluster.shim import RegionClusterService
from paasng.core.region.models import get_all_regions
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application, ModuleEnvironment


class BaseAppModelResourceCommand(BaseCommand):
    help = 'base command to handle bkapp'

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", help="应用 Code", default="", required=False)
        parser.add_argument("--module", dest="module_name", help="模块名称", default="default", required=False)
        parser.add_argument(
            "--region",
            dest="region",
            choices=list(get_all_regions().keys()),
            required=False,
            help="集群所在的 region, 当指定 cluster_name 时必须传递该参数;",
        )
        parser.add_argument("--cluster", dest="cluster_name", help="处理指定集群内的所有 BkApp", default="", required=False)
        parser.add_argument(
            "--all-clusters",
            dest="all_clusters",
            action="store_true",
            default=False,
            help="处理所有应用集群的所有 BkApp, 如果指定了 region, 将只处理 region 内的所有集群",
        )
        parser.add_argument("--no-dry-run", dest="dry_run", default=True, action="store_false", help="是否只打印带存储的环境变量信息")

    def handle(self, app_code, module_name, region, cluster_name, all_clusters, verbosity, dry_run, **options):
        raise NotImplementedError

    def validate_params(self, app_code, module_name, region, cluster_name, all_clusters) -> QuerySet:
        """Validate all parameter combinations, return the filtered ModuleEnvironment QuerySet"""
        if cluster_name != "":
            if app_code:
                raise CommandError("'cluster_name' and 'app_code' can't be used together.")
            if not region:
                raise CommandError("'region' is required when providing 'cluster_name'")
            # 验证集群存在
            cluster = RegionClusterService(region).get_cluster_by_name(cluster_name)
            # 查询集群下的所有 engine app
            # django 不支持跨库关联查询, 必须用 list 强制转换
            all_engine_app_ids = list(Config.objects.filter(cluster=cluster.name).values_list("app__uuid", flat=True))
            # 通过 engine app id 反查 ModuleEnvironment
            return ModuleEnvironment.objects.filter(
                application__type=ApplicationType.CLOUD_NATIVE, engine_app_id__in=all_engine_app_ids
            )
        elif all_clusters:
            return ModuleEnvironment.objects.filter(application__type=ApplicationType.CLOUD_NATIVE)
        else:
            app = Application.objects.get(code=app_code, type=ApplicationType.CLOUD_NATIVE)
            module = app.get_module(module_name)
            return ModuleEnvironment.objects.filter(application=app, module=module).all()
