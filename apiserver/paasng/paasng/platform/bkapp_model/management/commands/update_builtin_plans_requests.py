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
        parser.add_argument("--cpu", type=str, required=True, help="CPU requests (e.g., '200m')")
        parser.add_argument("--memory", type=str, required=True, help="Memory requests (e.g., '256Mi')")

    def handle(self, cpu, memory, *args, **options):
        slz = ResourceQuotaSLZ(data={"cpu": cpu, "memory": memory})
        if not slz.is_valid():
            raise CommandError(f"Invalid input: {slz.errors}")

        new_requests = slz.validated_data
        ResQuotaPlan.objects.filter(is_builtin=True).update(requests=new_requests, updated=timezone.now())

        self.stdout.write(self.style.SUCCESS(f"Successfully updated builtin plans with requests={new_requests}"))
