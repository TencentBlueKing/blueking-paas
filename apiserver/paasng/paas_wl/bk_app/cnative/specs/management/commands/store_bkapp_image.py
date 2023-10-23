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
from typing import TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.image_parser import ImageParser
from paas_wl.bk_app.cnative.specs.management.base import BaseAppModelResourceCommand
from paas_wl.bk_app.cnative.specs.models import AppModelResource
from paasng.platform.modules.models import BuildConfig, Module

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment  # noqa: F401


class Command(BaseAppModelResourceCommand):
    help = 'Store BkApp spec.build to BuildConfig'

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

        for module, revision in module_bkapp_pairs.values():
            self.store_build_to_db(module, revision, verbosity=verbosity, dry_run=dry_run)

    def store_build_to_db(self, module: Module, res: AppModelResource, verbosity: int, dry_run: bool = True):
        """Store spec.build defined at bkapp to db"""
        bkapp = BkAppResource(**res.revision.json_value)
        if not bkapp.spec.build:
            if verbosity >= 2:
                self.stdout.write("missing spec.build, skip")
            return

        try:
            image_repository = ImageParser(bkapp).get_repository()
            credential_name = bkapp.spec.build.imageCredentialsName
        except ValueError:
            self.stdout.write(
                self.style.ERROR("failed to parse image repository for app<{app_code}> module<{module_name}>").format(
                    app_code=module.application.code,
                    module_name=module.name,
                )
            )
            return

        prefix = "" if not dry_run else "DRY-RUN: "
        self.stdout.write(
            self.style.NOTICE(
                "{prefix}store spec.build for app<{app_code}> module<{module_name}>".format(
                    prefix=prefix,
                    app_code=module.application.code,
                    module_name=module.name,
                )
            )
        )
        # Verbosity level, 2=verbose output
        if verbosity >= 2:
            self.stdout.write(
                self.style.WARNING(
                    "{prefix} set image_repository={image_repository}, image_credential_name={credential_name}".format(
                        prefix=prefix,
                        image_repository=image_repository,
                        credential_name=credential_name,
                    )
                )
            )
        if not dry_run:
            cfg = BuildConfig.objects.get_or_create_by_module(module)
            cfg.image_repository = image_repository
            cfg.image_credential_name = credential_name
            cfg.save(update_fields=["image_repository", "image_credential_name", "updated"])
