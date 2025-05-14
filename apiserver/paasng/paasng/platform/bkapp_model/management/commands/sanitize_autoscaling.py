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
from typing import Dict

from django.core.management.base import BaseCommand

from paas_wl.bk_app.processes.models import ProcessSpec
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay

logger = logging.getLogger("commands")

ACTION_DISPLAY = "display"
ACTION_UPDATE = "update"


class Command(BaseCommand):
    help = "Sanitize autoscaling config data that spreads in different models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--action", choices=[ACTION_DISPLAY, ACTION_UPDATE], required=True, type=str, help="Name of action"
        )

    def handle(self, *args, **options):
        if options["action"] == ACTION_UPDATE:
            return self.handle_update()
        elif options["action"] == ACTION_DISPLAY:
            return self.handle_display()
        raise RuntimeError("Invalid action")

    def handle_update(self):
        print("Start updating ProcessSpec model...")
        for obj in ProcessSpec.objects.all():
            if c := obj.scaling_config:
                obj.scaling_config = self.sanitize_config(c)
                obj.save(update_fields=["scaling_config"])

        print("Start updating ModuleProcessSpec model...")
        for module_spec in ModuleProcessSpec.objects.all():
            if c := module_spec.scaling_config:
                module_spec.scaling_config = self.sanitize_config(c)
                module_spec.save(update_fields=["scaling_config"])

        print("Start updating ProcessSpecEnvOverlay model...")
        for overlay_spec in ProcessSpecEnvOverlay.objects.all():
            if c := overlay_spec.scaling_config:
                overlay_spec.scaling_config = self.sanitize_config(c)
                overlay_spec.save(update_fields=["scaling_config"])

    def handle_display(self):
        print("> ProcessSpec model:")
        for obj in ProcessSpec.objects.all():
            if obj.scaling_config:
                print(obj.scaling_config)

        print("> ModuleProcessSpec model:")
        for module_spec in ModuleProcessSpec.objects.all():
            if module_spec.scaling_config:
                print(module_spec.scaling_config)

        print("> ProcessSpecEnvOverlay model:")
        for overlay_spec in ProcessSpecEnvOverlay.objects.all():
            if overlay_spec.scaling_config:
                print(overlay_spec.scaling_config)

    @staticmethod
    def sanitize_config(c: Dict):
        """Sanitize the config."""
        result = {
            "min_replicas": c.get("min_replicas") or c.get("minReplicas") or 1,
            "max_replicas": c.get("max_replicas") or c.get("maxReplicas") or 1,
            "policy": "default",
        }
        return result
