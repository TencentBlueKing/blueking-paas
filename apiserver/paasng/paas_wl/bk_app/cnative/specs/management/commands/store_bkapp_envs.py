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
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db.models import QuerySet

from paas_wl.bk_app.applications.models import Config
from paas_wl.bk_app.cnative.specs.configurations import EnvVarsReader
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.models import AppModelResource
from paas_wl.infras.cluster.shim import RegionClusterService
from paasng.core.region.models import get_all_regions
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.models.managers import ConfigVarManager
from paasng.platform.modules.models import Module


class Command(BaseCommand):
    help = 'Store BkApp Configration.env to databases'

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
        try:
            filtered_envs = self._validate_params(app_code, module_name, region, cluster_name, all_clusters)
        except ObjectDoesNotExist:
            raise CommandError("can't get bkapp with given params")

        module_bkapp_pairs = {}
        for module_env in filtered_envs:  # type: ModuleEnvironment
            module_id = module_env.module_id
            if module_id in module_bkapp_pairs:
                continue
            try:
                res = AppModelResource.objects.get(module_id=module_id)
            except ObjectDoesNotExist:
                self.stderr.write(
                    self.style.ERROR(
                        "app<{app_code}> module<{module_name}> do not have AppModelResource".format(
                            app_code=module_env.application.code,
                            module_name=module_env.module.name,
                        )
                    )
                )
                continue
            module_bkapp_pairs[module_id] = (module_env.module, res)

        if not module_bkapp_pairs:
            self.stdout.write(self.style.WARNING("nothing to handle"))
            return

        for module, revision in module_bkapp_pairs.values():
            self.store_envs_to_db(module, revision, verbosity=verbosity, dry_run=dry_run)

    def store_envs_to_db(self, module: Module, res: AppModelResource, verbosity: int, dry_run: bool = True):
        """Store all env var defined at bkapp to db"""
        config_vars = []
        bkapp = BkAppResource(**res.revision.json_value)
        config_vars = EnvVarsReader(bkapp).read_all(module)

        if not dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    "apply vars to app<{app_code}> module<{module_name}>".format(
                        app_code=module.application.code,
                        module_name=module.name,
                    )
                )
            )
            ConfigVarManager().apply_vars_to_module(module, config_vars=config_vars)
            # clear Configration.env and envOverlay.envVariables
            bkapp.spec.configuration.env = []
            if bkapp.spec.envOverlay:
                bkapp.spec.envOverlay.envVariables = []
            # save as new revision
            res.use_resource(bkapp)
        else:
            self.stdout.write(
                self.style.NOTICE(
                    "DRY-RUN: apply vars to app<{app_code}> module<{module_name}>".format(
                        app_code=module.application.code,
                        module_name=module.name,
                    )
                )
            )
            # Verbosity level, 2=verbose output
            if verbosity >= 2:
                for config_var in config_vars:
                    self.stdout.write(
                        self.style.WARNING(
                            "DRY-RUN: saving for env<{env}> key<{key}>".format(
                                env=config_var.environment_name,
                                key=config_var.key,
                            )
                        )
                    )

    def _validate_params(self, app_code, module_name, region, cluster_name, all_clusters) -> QuerySet:
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
