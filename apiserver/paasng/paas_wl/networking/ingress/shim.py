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

from paas_wl.networking.entrance.allocator.domains import ModuleEnvDomains
from paas_wl.networking.entrance.allocator.subpaths import ModuleEnvSubpaths
from paas_wl.networking.ingress.managers import assign_custom_hosts, assign_subpaths
from paas_wl.networking.ingress.models import AutoGenDomain
from paas_wl.networking.ingress.utils import guess_default_service_name
from paasng.platform.applications.models import ModuleEnvironment


def sync_subpaths(env: ModuleEnvironment):
    subpaths = ModuleEnvSubpaths(env).all()
    # TODO: 弄清楚为什么 subpath 为空时不同步
    if subpaths:
        wl_app = env.wl_app
        default_service_name = guess_default_service_name(wl_app)
        # Assign subpaths to app
        subpath_vals = [d.subpath for d in subpaths]
        assign_subpaths(wl_app, subpath_vals, default_service_name=default_service_name)


def sync_subdomains(env: ModuleEnvironment):
    domains = ModuleEnvDomains(env).all()
    wl_app = env.wl_app
    default_service_name = guess_default_service_name(wl_app)
    # Assign domains to app
    domain_objs = [AutoGenDomain(host=d.host, https_enabled=d.https_enabled) for d in domains]
    assign_custom_hosts(wl_app, domains=domain_objs, default_service_name=default_service_name)
