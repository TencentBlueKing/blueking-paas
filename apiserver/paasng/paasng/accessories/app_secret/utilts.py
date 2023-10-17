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
import typing
from datetime import datetime
from typing import List, Optional

from django.conf import settings

from paas_wl.bk_app.processes.shim import ProcessManager
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.constants import AppInfoBuiltinEnv
from paasng.platform.engine.utils.query import DeploymentGetter

if typing.TYPE_CHECKING:
    from paas_wl.bk_app.processes.entities import Instance


def get_latest_deployed_at(env: ModuleEnvironment) -> Optional[datetime]:
    latest_deployment = DeploymentGetter(env).get_latest_succeeded()
    if latest_deployment:
        return latest_deployment.created
    return None


def get_app_secret_in_instance(ins_list: List['Instance']) -> Optional[str]:
    """获取进程实例中环境变量中的应用密钥(BKPAAS_APP_SECRET)的值"""
    if not ins_list:
        return None
    return ins_list[0].envs.get(f"{settings.CONFIGVAR_SYSTEM_PREFIX}{AppInfoBuiltinEnv.APP_SECRET}")


def get_deployed_secret_list(application: Application) -> list:
    """查询应用各个模块、环境下内置环境变量 BKPAAS_APP_SECRET 的值"""
    envs = ModuleEnvironment.objects.filter(module__in=application.modules.all()).all()
    deployed_secret_list = []

    for env in envs:
        # 获取当前环境下的所有进程，以便从进程中获取环境变量信息
        process_manager = ProcessManager(env)
        process_list = process_manager.list_processes()
        if not process_list:
            continue

        # 当前环境的最近部署成功的时间
        latest_deployed_at = get_latest_deployed_at(env)

        # 查询进程中的环境变量信息，只需查询到一个即可
        bk_app_secret = None
        for process in process_list:
            bk_app_secret = get_app_secret_in_instance(process.instances)
            if bk_app_secret:
                break

        if bk_app_secret is not None:
            deployed_secret_list.append(
                {
                    "module": env.module.name,
                    "environment": env.environment,
                    "bk_app_secret": bk_app_secret,
                    "latest_deployed_at": latest_deployed_at,
                }
            )
    return deployed_secret_list
