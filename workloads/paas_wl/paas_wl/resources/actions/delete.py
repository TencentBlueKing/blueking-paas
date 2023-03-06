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
from paas_wl.resources.utils.app import get_scheduler_client_by_app
from paas_wl.workloads.processes.controllers import module_env_is_running
from paasng.platform.applications.models import ModuleEnvironment


def delete_env_resources(env: 'ModuleEnvironment'):
    """Delete app's resources in cluster"""
    if not module_env_is_running(env):
        return

    wl_app = env.wl_app
    scheduler_client = get_scheduler_client_by_app(app=wl_app)
    scheduler_client.delete_all_under_namespace(namespace=wl_app.namespace)
    return
