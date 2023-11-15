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
from typing import Dict, List

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from paas_wl.apis.admin.serializers.processes import InstanceSerializer, ProcessSpecPlanSLZ
from paas_wl.bk_app.processes.models import ProcessSpecPlan
from paas_wl.bk_app.processes.shim import ProcessManager
from paasng.core.region.models import get_all_regions
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName
from paasng.utils.text import remove_prefix


def get_path(request: Request) -> str:
    path = request.path
    if settings.FORCE_SCRIPT_NAME:
        path = remove_prefix(path, settings.FORCE_SCRIPT_NAME)
    path = remove_prefix(path, "/")
    return path


class ProcessSpecPlanManageView(GenericTemplateView):
    """ProcessSpecPlan 管理页"""

    name = "应用资源方案"
    serializer_class = ProcessSpecPlanSLZ
    queryset = ProcessSpecPlan.objects.all()
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    template_name = "admin42/platformmgr/process_spec_plans.html"

    def get_context_data(self, **kwargs):
        self.paginator.default_limit = 2
        self.paginator.request = self.request
        kwargs.update(self.request.query_params)
        if 'view' not in kwargs:
            kwargs['view'] = self

        kwargs["env_choices"] = [{"value": value, "text": text} for value, text in AppEnvName.get_choices()]
        kwargs["region_list"] = [
            {"value": region.name, "text": region.display_name} for region in get_all_regions().values()
        ]
        kwargs["process_spec_plan_list"] = self.list(self.request, *self.args, **self.kwargs)
        kwargs['pagination'] = self.get_pagination_context(self.request)
        return kwargs

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ProcessSpecManageView(ApplicationDetailBaseView):
    """应用 ProcessSpec 管理页"""

    name = "进程管理"
    template_name = "admin42/applications/detail/engine/processes.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        application = self.get_application()
        envs = ModuleEnvironment.objects.filter(module__in=application.modules.all()).all()
        processes: List[Dict] = []

        for env in envs:
            process_manager = ProcessManager(env)
            process_spec_map = {}
            for process_spec in process_manager.list_processes_specs():
                process_spec_map[process_spec["name"]] = process_spec

            process_map = {}
            for process in process_manager.list_processes():
                process_spec = process_spec_map[process.type]
                process_map[process.type] = {
                    "engine_app": env.engine_app.name,
                    "type": process.type,
                    "metadata": {
                        "module": env.module.name,
                        "env": env.environment,
                    },
                    "desired_replicas": process.replicas,
                    "command": process.runtime.proc_command,
                    "available_instance_count": process.available_instance_count,
                    "instances": InstanceSerializer(process.instances, many=True).data,
                }
                if application.type != ApplicationType.CLOUD_NATIVE:
                    process_map[process.type]["process_spec"] = {
                        "plan": {
                            "id": ProcessSpecPlan.objects.get_by_name(process_spec["plan_name"]).pk,
                            "name": process_spec["plan_name"],
                            "limits": process_spec["resource_limit"],
                            "requests": process_spec["resource_requests"],
                            "max_replicas": process_spec["max_replicas"],
                        }
                    }
            processes.extend(process_map.values())

        kwargs["processes"] = processes
        return kwargs

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
