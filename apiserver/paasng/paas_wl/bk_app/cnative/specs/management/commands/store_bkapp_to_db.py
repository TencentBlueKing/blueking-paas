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

import logging
from typing import TYPE_CHECKING

import yaml
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError
from rest_framework.serializers import ValidationError

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.management.base import BaseAppModelResourceCommand
from paas_wl.bk_app.cnative.specs.models import AppModelResource
from paasng.platform.bkapp_model.fieldmgr import FieldMgrName
from paasng.platform.bkapp_model.importer import import_manifest_yaml
from paasng.platform.bkapp_model.serializers.v1alpha2 import BkAppSpecInputSLZ
from paasng.platform.modules.models import Module

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment  # noqa: F401


class Command(BaseAppModelResourceCommand):
    help = "Store BkApp Specs to databases"

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
            try:
                self.import_bkapp(module, res, verbosity=verbosity, dry_run=dry_run)
            except Exception:
                logging.exception("")

    def import_bkapp(self, module: Module, res: AppModelResource, verbosity: int, dry_run: bool = True):
        """import bkapp manifest"""
        bkapp = BkAppResource(**res.revision.json_value)
        input_data = bkapp.json(exclude_none=True, indent=2, ensure_ascii=False)

        prefix = "" if not dry_run else "DRY-RUN: "
        self.stdout.write(
            self.style.NOTICE(
                "{prefix}import manifest to app<{app_code}> module<{module_name}>".format(
                    prefix=prefix,
                    app_code=module.application.code,
                    module_name=module.name,
                )
            )
        )
        # dry_run validate json_value
        if dry_run:
            manifest = yaml.safe_load(input_data)
            spec_slz = BkAppSpecInputSLZ(data=manifest["spec"])
            try:
                spec_slz.is_valid(raise_exception=True)
            except ValidationError as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"{prefix}import manifest to app<{module.application.code}> module<{module.name}> failed: {e}"
                    )
                )

        # Verbosity level, 2=verbose output
        if verbosity >= 2:
            self.stdout.write(
                self.style.WARNING(
                    "{prefix}Manifest START: \n{manifest}\n{prefix}Manifest END".format(
                        prefix=prefix,
                        manifest=input_data,
                    )
                )
            )
        if not dry_run:
            import_manifest_yaml(module=module, input_yaml_data=input_data, manager=FieldMgrName.APP_DESC)
