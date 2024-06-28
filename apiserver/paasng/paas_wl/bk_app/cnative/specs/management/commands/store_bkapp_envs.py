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

from typing import TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError

from paas_wl.bk_app.cnative.specs.configurations import EnvVarsReader
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.management.base import BaseAppModelResourceCommand
from paas_wl.bk_app.cnative.specs.models import AppModelResource
from paasng.platform.engine.models.managers import ConfigVarManager
from paasng.platform.modules.models import Module

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment  # noqa: F401


class Command(BaseAppModelResourceCommand):
    help = "Store BkApp Configration.env to databases"

    def handle(self, app_code, module_name, region, cluster_name, all_clusters, verbosity, dry_run, **options):
        try:
            filtered_envs = self.validate_params(app_code, module_name, region, cluster_name, all_clusters)
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

        for module, res in module_bkapp_pairs.values():
            self.store_envs_to_db(module, res, verbosity=verbosity, dry_run=dry_run)

    def store_envs_to_db(self, module: Module, res: AppModelResource, verbosity: int, dry_run: bool = True):
        """Store all env var defined at bkapp to db"""
        bkapp = BkAppResource(**res.revision.json_value)
        config_vars = EnvVarsReader(bkapp).read_all(module)

        prefix = "" if not dry_run else "DRY-RUN: "
        self.stdout.write(
            self.style.NOTICE(
                "{prefix}apply vars to app<{app_code}> module<{module_name}>".format(
                    prefix=prefix,
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
                        "{prefix}saving for env<{env}> key<{key}>".format(
                            prefix=prefix,
                            env=config_var.environment_name,
                            key=config_var.key,
                        )
                    )
                )
        if not dry_run:
            ConfigVarManager().apply_vars_to_module(module, config_vars=config_vars)
            # clear Configration.env and envOverlay.envVariables
            bkapp.spec.configuration.env = []
            if bkapp.spec.envOverlay:
                bkapp.spec.envOverlay.envVariables = []
            # save as new revision
            res.use_resource(bkapp)
