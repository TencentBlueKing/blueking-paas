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
"""
A command for exporting environment variables(or so called config vars) to a Blueking Application
"""
import argparse
import sys

from django.core.management.base import BaseCommand

from paasng.engine.models.managers import ExportedConfigVars
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    """导出应用环境变量"""

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", required=True, help="应用code")
        parser.add_argument("--module", dest="module_name", required=True, help="模块名称")
        parser.add_argument(
            "-f",
            "--file",
            dest="file_",
            default=sys.stdout,
            type=argparse.FileType("w"),
            help="环境变量导出生成的文件存放的路径, 默认值为标准输出",
        )

    def handle(self, app_code, module_name, file_, *args, **options):
        application = Application.objects.get(code=app_code)
        module = application.get_module(module_name=module_name)

        qs = module.configvar_set.filter(is_builtin=False).select_related('environment')
        exported = ExportedConfigVars.from_list(list(qs))

        with file_ as fh:
            fh.write(exported.to_file_content())
