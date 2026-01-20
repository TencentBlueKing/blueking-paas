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

from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError

from paasng.plat_mgt.res_quota_plan.serializers import ResQuotaPlanInputSLZ
from paasng.platform.bkapp_model.models import ResQuotaPlan


class Command(BaseCommand):
    help = "Update limits and requests of builtin resource quota plans."

    def add_arguments(self, parser):
        parser.add_argument("--name", type=str, required=True, help="Name of the builtin plan to update.")
        parser.add_argument("--cpu_limits", type=str, required=True, help="CPU limits (e.g., '4000m')")
        parser.add_argument("--memory_limits", type=str, required=True, help="Memory limits (e.g., '2048Mi')")
        parser.add_argument("--cpu_requests", type=str, required=True, help="CPU requests (e.g., '200m')")
        parser.add_argument("--memory_requests", type=str, required=True, help="Memory requests (e.g., '256Mi')")

    def handle(self, name, cpu_limits, memory_limits, cpu_requests, memory_requests, *args, **options):
        try:
            plan = ResQuotaPlan.objects.get(name=name, is_builtin=True)
        except ResQuotaPlan.DoesNotExist:
            raise CommandError(f"Builtin plan with name '{name}' does not exist.")

        data = {
            "name": name,
            "limits": {"cpu": cpu_limits, "memory": memory_limits},
            "requests": {"cpu": cpu_requests, "memory": memory_requests},
        }
        slz = ResQuotaPlanInputSLZ(data=data, instance=plan)
        try:
            slz.is_valid(raise_exception=True)
        except ValidationError as err:
            raise CommandError(f"Invalid data: {err.detail}") from err

        validated_data = slz.validated_data
        plan.limits = validated_data["limits"]
        plan.requests = validated_data["requests"]
        plan.save(update_fields=["limits", "requests", "updated"])

        self.stdout.write(self.style.SUCCESS(f"Successfully updated builtin plan '{name}'."))
