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
from django.utils import timezone

from paasng.plat_mgt.res_quota_plan.serializers import ResourceQuotaSLZ
from paasng.platform.bkapp_model.models import ResQuotaPlan


class Command(BaseCommand):
    help = "Update requests of all builtin resource quota plans."

    def add_arguments(self, parser):
        parser.add_argument("--cpu", type=str, required=False, help="CPU requests (e.g., '200m')")
        parser.add_argument("--memory", type=str, required=False, help="Memory requests (e.g., '256Mi')")

    def handle(self, cpu, memory, *args, **options):
        if not cpu and not memory:
            raise CommandError("At least one of --cpu or --memory must be provided")

        # dummy value just for validation
        input_data = {"cpu": "1m", "memory": "1Mi"}
        # 用实际值覆盖 dummy value
        if cpu:
            input_data["cpu"] = cpu
        if memory:
            input_data["memory"] = memory

        slz = ResourceQuotaSLZ(data=input_data)
        if not slz.is_valid():
            raise CommandError(f"Invalid input: {slz.errors}")

        for plan in ResQuotaPlan.objects.filter(is_builtin=True):
            if cpu:
                plan.requests["cpu"] = cpu
            if memory:
                plan.requests["memory"] = memory

            plan.updated = timezone.now()
            plan.save(update_fields=["requests", "updated"])

        self.stdout.write(self.style.SUCCESS("Successfully update requests of all builtin resource quota plans"))
