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

"""
A command for importing environment variables(or so called config vars) to a Blueking Application
"""
import argparse

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from paasng.platform.applications.models import Application
from paasng.platform.engine.models.managers import ConfigVarManager
from paasng.platform.engine.serializers import ConfigVarImportSLZ


class Command(BaseCommand):
    """导入应用环境变量"""

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", required=True, help="应用code")
        parser.add_argument("--module", dest="module_name", required=True, help="模块名称")
        parser.add_argument(
            "-f",
            "--file",
            dest="file_",
            required=True,
            type=argparse.FileType(),
            help="环境变量的 yaml 文件路径",
        )

    def handle(self, app_code, module_name, file_, *args, **options):
        application = Application.objects.get(code=app_code)
        module = application.get_module(module_name=module_name)

        with file_ as fh:
            slz = ConfigVarImportSLZ(
                data={"file": ContentFile(fh.read(), name=getattr(file_, "name", "dummy"))}, context={"module": module}
            )
            slz.is_valid(raise_exception=True)

            env_variables = slz.validated_data["env_variables"]
            apply_result = ConfigVarManager().apply_vars_to_module(module=module, config_vars=env_variables)

            self.stdout.write(
                f"Successfully created {apply_result.create_num} environment variables and "
                f"overwrote {apply_result.overwrited_num} environment variables"
            )
            self.stdout.write(f"Ignore {apply_result.ignore_num} environment variables because of existing already.")
