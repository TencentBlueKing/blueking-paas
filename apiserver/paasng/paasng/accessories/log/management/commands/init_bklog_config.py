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

from paasng.accessories.log.shim import setup_env_log_model
from paasng.platform.applications.models import ModuleEnvironment


class Command(BaseCommand):
    """初始化日志采集配置，默认处理所有应用"""

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", help="应用ID，不填则为所有应用", default="", required=False)
        parser.add_argument(
            "--module", dest="module_name", help="模块名称，不填则为应用下所有模块", default="", required=False
        )

    def handle(self, app_code, module_name, **options):
        try:
            filtered_envs = self.validate_params(app_code, module_name)
        except ObjectDoesNotExist:
            raise CommandError("can't get bkapp with given params")

        for module_env in filtered_envs:  # type: ModuleEnvironment
            setup_env_log_model(module_env)
            self.stdout.write(
                self.style.NOTICE(
                    "init bklog config:<{app_code}> module<{module_name}>env<{env}>".format(
                        app_code=module_env.application.code,
                        module_name=module_env.module.name,
                        env=module_env.environment,
                    )
                )
            )

    def validate_params(self, app_code, module_name) -> QuerySet:
        all_envs = ModuleEnvironment.objects.all()
        # 未指定应用，则处理所有应用下所有模块
        if not app_code:
            return all_envs

        if app_code:
            all_envs = all_envs.filter(application__code=app_code)
        if module_name:
            all_envs = all_envs.filter(module__name=module_name)
        return all_envs
