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

"""Generates RCStateAppBinding for WlApp

Examples:

    python manage.py create_rc_state_binding --code app-code-1 --module default --env stag
"""
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.workloads.networking.egress.models import RCStateAppBinding, RegionClusterState
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = "Generates RCStateAppBinding for WlApp"

    def add_arguments(self, parser):
        parser.add_argument("--code", dest="app_code", required=True, help="应用 Code")
        parser.add_argument("--module", dest="module_name", required=True, help="模块名称")
        parser.add_argument("--env", dest="environment", required=True, help="部署环境", choices=["stag", "prod"])

    def handle(self, app_code, module_name, environment, *args, **options):
        application = Application.objects.get(code=app_code)
        module = application.get_module(module_name)
        wl_app = module.get_envs(environment).engine_app.to_wl_obj()

        cluster = get_cluster_by_app(wl_app)
        try:
            state = RegionClusterState.objects.filter(region=wl_app.region, cluster_name=cluster.name).latest()
            RCStateAppBinding.objects.create(app=wl_app, state=state)
        except RegionClusterState.DoesNotExist:
            print("Cluster data is not initialized, please try again later")
        except IntegrityError:
            print("Can't bound for the same WlApp more than once")
        else:
            print(f"Bound successfully, wl_app: {wl_app}, state: {state}")
