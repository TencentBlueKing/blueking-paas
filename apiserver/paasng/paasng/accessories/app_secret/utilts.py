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
from django.conf import settings

from paas_wl.workloads.processes.shim import ProcessManager
from paasng.engine.constants import AppInfoBuiltinEnv
from paasng.engine.utils.query import DeploymentGetter
from paasng.platform.applications.models import Application, ModuleEnvironment


def get_deployed_secret_list(application: Application) -> list:
    """查询应用各个模块、环境下内置环境变量 BKPAAS_APP_SECRET 的值"""
    envs = ModuleEnvironment.objects.filter(module__in=application.modules.all()).all()
    deployed_secret_list = []
    for env in envs:
        # 当前环境的最近部署成功的时间
        latest_deployed_at = None
        latest_deployment = DeploymentGetter(env).get_latest_succeeded()
        if latest_deployment:
            latest_deployed_at = latest_deployment.created

        # 查询线上运行进程中的环境变量信息
        process_manager = ProcessManager(env)
        process_list = process_manager.list_processes()
        # 只查询一个进程的内置密钥即可
        _secret = process_list[0].runtime.envs.get(f"{settings. EnvVar_SYSTEM_PREFIX}{AppInfoBuiltinEnv.APP_SECRET}")
        deployed_secret_list.append(
            {
                "module": env.module.name,
                "environment": env.environment,
                "bk_app_secret": _secret,
                "latest_deployed_at": latest_deployed_at,
            }
        )
    return deployed_secret_list
