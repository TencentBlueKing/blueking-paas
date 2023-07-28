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
"""Convert bkapp from v1alpha1 to v1alpha2

Examples:

    # 仅转换指定的 BkApp
    python manage.py convert_bkapp_version --code app-code-1 --module default

    # 检查所有存量 BkApp 配置，打印可转换的 BkApp 信息
    python manage.py convert_bkapp_version --all-bkapp --dry-run

    # 检查并转换所有符合条件的 BkApp 配置
    python manage.py convert_bkapp_version --all-bkapp
"""
from django.core.management.base import BaseCommand

from paas_wl.cnative.specs.converter import BkAppResourceConverter
from paas_wl.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.cnative.specs.models import AppModelResource
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = 'Convert BkApp version. Only v1alpha1 -> v1alpha2 supported'

    def add_arguments(self, parser):
        parser.add_argument("--code", dest="app_code", help="应用 Code")
        parser.add_argument("--module", dest="module_name", help="模块名称")
        parser.add_argument("--all-bkapp", dest="all_bkapp", help="是否检查并转换所有 BkApp", action="store_true")
        parser.add_argument("--dry-run", dest="dry_run", help="是否只打印待转换的 BkApp 信息", action="store_true")

    def handle(self, app_code, module_name, all_bkapp, dry_run, *args, **options):
        self._validate_params(app_code, module_name, all_bkapp)

        resources = AppModelResource.objects.all()
        if app_code and module_name:
            app = Application.objects.get(code=app_code)
            module = app.get_module(module_name=module_name)
            resources = resources.filter(application_id=app.id, module_id=module.id)

        for res in resources:
            bkapp_res = BkAppResource(**res.revision.json_value)
            print(f"will try convert BkApp {bkapp_res.metadata.name}")

        if dry_run:
            print("============ dry run ============")
            return

        for res in resources:
            bkapp_res = BkAppResource(**res.revision.json_value)
            bkapp_res, converted, upgrade_version = BkAppResourceConverter(bkapp_res).convert()
            res.use_resource(bkapp_res)

            bkapp_name = bkapp_res.metadata.name
            if converted:
                print(f"BkApp {bkapp_name} converted")
            if not upgrade_version:
                print(f"BkApp {bkapp_name} still in v1alpha1 version due to use multi-images")

    def _validate_params(self, app_code: str, module_name: str, all_bkapp: bool):
        if not all_bkapp and not (app_code and module_name):
            raise ValueError("code and module is required when all-bkapp is False")
