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

from django.core.management.base import BaseCommand

from paas_wl.bk_app.applications.api import update_metadata_by_env
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Aim to inject app metadata for all engine apps"

    def handle(self, *args, **options):
        logger.info("Going to update all meta info...")
        all_modules = Module.objects.all()

        updated_count = 0
        exception_count = 0
        skip_count = 0
        for module in all_modules:
            initializer = ModuleInitializer(module=module)
            for env in ModuleInitializer.default_environments:
                try:
                    env_obj = module.get_envs(environment=env)
                except Exception:
                    # 精简版应用是没有 AppEnv 的
                    logger.exception("unable to get engine_app for %s:%s", module.application.code, env)
                    skip_count += 1
                    continue

                # EngineApp 元信息，理论上不会变更，所以可以直接覆盖
                engine_app_meta_info = initializer.make_engine_meta_info(env_obj)
                try:
                    update_metadata_by_env(env_obj, engine_app_meta_info)
                    updated_count += 1
                    logger.info(f"update metadata{engine_app_meta_info} successful")
                except Exception:
                    logger.exception("update meta info failed")

                    exception_count += 1
                    continue

        logger.info("update done. %s updated, %s failed %s skip.", updated_count, exception_count, skip_count)
