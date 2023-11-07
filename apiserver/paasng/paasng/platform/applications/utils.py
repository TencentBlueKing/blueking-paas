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
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from django.db import transaction

from paas_wl.bk_app.cnative.specs.models import AppModelDeploy
from paas_wl.bk_app.processes.shim import ProcessManager
from paasng.accessories.publish.entrance.exposer import env_is_deployed, get_exposed_url
from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.accessories.publish.market.models import MarketConfig
from paasng.core.region.models import get_region
from paasng.infras.oauth2.utils import create_oauth2_client
from paasng.platform.applications.constants import AppEnvironment, ApplicationType
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.applications.signals import post_create_application, pre_delete_module
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.modules.constants import ModuleName, SourceOrigin
from paasng.platform.modules.manager import ModuleCleaner
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


def create_default_module(
    application: Application,
    language: str = '',
    source_init_template: str = '',
    source_origin: SourceOrigin = SourceOrigin.AUTHORIZED_VCS,
) -> Module:
    """Create the default module for application

    :param language: programming language of source init template
    :param source_init_template: source init template name, when it's empty, all source template related steps will be
        skipped.
    :param source_origin: The origin of module's source code
    """
    region = get_region(application.region)
    language = language or application.language
    module = Module.objects.create(
        application=application,
        name=ModuleName.DEFAULT.value,
        is_default=True,
        region=application.region,
        owner=application.owner,
        creator=application.creator,
        # Extra fields
        source_origin=source_origin.value,
        language=language,
        source_init_template=source_init_template,
        exposed_url_type=region.entrance_config.exposed_url_type,
    )
    return module


def delete_module_and_resources(module: Module, operator: str):
    cleaner = ModuleCleaner(module)

    logger.info("going to delete services related to Module<%s>", module)
    cleaner.delete_services()

    logger.info("going to delete EngineApp related to Module<%s>", module)
    cleaner.delete_engine_apps()

    # 数据记录删除(module 是真删除)
    logger.info("going to delete Module<%s>")
    cleaner.delete_module()


def delete_module(application: Application, module_name: str, operator: str):
    with transaction.atomic():
        module = application.get_module_with_lock(module_name=module_name)
        delete_module_and_resources(module, operator)


def delete_all_modules(application: Application, operator: str):
    """删除应用下的所有 Module"""
    modules = application.modules.all()
    for module in modules:
        pre_delete_module.send(sender=Module, module=module, operator=operator)
        delete_module_and_resources(module, operator)


def create_application(
    region: str,
    code: str,
    name: str,
    name_en: str,
    type_: str,
    operator: str,
):
    """创建 Application 模型"""
    application = Application.objects.create(
        type=type_,
        owner=operator,
        creator=operator,
        region=region,
        code=code,
        name=name,
        name_en=name_en,
    )
    create_oauth2_client(application.code, application.region)

    return application


def create_market_config(
    application: Application,
    source_url_type: ProductSourceUrlType,
    source_tp_url: Optional[str] = None,
    prefer_https: bool = False,
) -> MarketConfig:
    """创建市场模型"""
    app_specs = AppSpecs(application)
    # Create market related data after application created, to avoid market related data be covered
    confirm_required_when_publish = app_specs.confirm_required_when_publish
    return MarketConfig.objects.create(
        region=application.region,
        application=application,
        # 即使启用应用市场服务, 但新创建App时, 应用推广信息未填写, 因此设置为 False, 后续由开发者在应用推广页面重新打开
        enabled=False,
        # 当 auto_enable_when_deploy 为 True 时, 部署后即自动上架到市场; 否则就不会
        auto_enable_when_deploy=not confirm_required_when_publish,
        source_module=application.get_default_module(),
        source_url_type=source_url_type.value,
        source_tp_url=source_tp_url or '',
        prefer_https=prefer_https,
    )


@transaction.atomic
def create_third_app(
    region: str, code: str, name: str, name_en: str, operator: str, market_params: Optional[dict] = None
) -> Application:
    """创建第三方（外链）应用"""
    if market_params is None:
        market_params = {}

    application = create_application(
        region=region,
        code=code,
        name=name,
        name_en=name_en,
        type_=ApplicationType.ENGINELESS_APP.value,
        operator=operator,
    )
    create_default_module(application)

    post_create_application.send(sender=create_third_app, application=application)

    create_market_config(
        application=application,
        # 外链应用, 基于第三方访问地址进行访问
        source_url_type=ProductSourceUrlType.THIRD_PARTY,
        source_tp_url=market_params.get("source_tp_url", ""),
    )
    return application


def get_app_overview(application: Application) -> dict:
    """普通应用、云原生应用的概览信息
    包含：每个模块下各个环境的访问地址和进程信息

    :returns: 示例 {
            'module_name': {
                'is_default': True,
                'envs': {
                    'stag': {
                        "is_deployed": True, # 是否部署
                        "exposed_link": {
                            "url": "http://apps.example.com/appid--stag/"
                        },
                        "processes": [
                            {
                                "web": {
                                    "name": "web",
                                    "target_replicas": 5, # 进程数
                                }
                            },
                        ]
                        "deployment": {
                            "operator": "admin",
                            "deploy_time": "2023-03-14 16:15:19"
                        }
                    },
                    'prod': {
                        "is_deployed": False, # 未部署，则不需要展示该模块的访问地址等信息
                        ....
                    }
                }
            }
        }
    """
    data = {}
    # 查询所有的模块
    modules = application.modules.all().order_by('-is_default', '-created')
    for module in modules:
        module_info = {'is_default': module.is_default, 'envs': {}}
        # 查看模块下每个环境的访问地址和进程信息
        for env in AppEnvironment.get_values():
            module_env = module.get_envs(environment=env)
            # 检查当前环境是否已部署
            is_deployed = env_is_deployed(module_env)
            exposed_link = get_exposed_url(module_env)

            # 进程信息
            _specs = ProcessManager(module_env).list_processes_specs()
            specs = [{spec['name']: spec} for spec in _specs]

            latest_dp = None
            if is_deployed:
                latest_dp = get_latest_deployment_basic_info(application, module_env)

            module_info['envs'][env] = {
                'is_deployed': is_deployed,
                'exposed_link': {"url": exposed_link.address if exposed_link else None},
                'processes': specs,
                'deployment': latest_dp,
            }

        data[module.name] = module_info
    return data


def get_latest_deployment_basic_info(application: Application, env: ModuleEnvironment) -> Optional[dict]:
    """获取应用的最近部署信息"""
    if application.type == ApplicationType.CLOUD_NATIVE.value:
        try:
            latest_dp = AppModelDeploy.objects.filter_by_env(env).latest("created")
        except AppModelDeploy.DoesNotExist:
            return None
    else:
        try:
            latest_dp = Deployment.objects.filter_by_env(env=env).latest_succeeded()
        except Deployment.DoesNotExist:
            return None

    # AppModelDeploy 和 Deployment 表中基本信息内容（operator、created）字段定义一致
    return {
        "operator": latest_dp.operator.username,
        "deploy_time": latest_dp.created.isoformat(sep=" ", timespec="seconds"),
    }


@dataclass
class ResQuotasAggregation:
    app: Application

    def get_resource_quotas(self) -> dict:
        quotas: dict = {"prod": defaultdict(int), "stag": defaultdict(int)}
        for app_env in self.app.get_app_envs():
            processes_specs = ProcessManager(app_env).list_processes_specs()

            for _specs in processes_specs:
                quotas[app_env.environment]["memory_total"] += (
                    _specs["resource_limit_quota"]['memory'] * _specs['target_replicas']
                )
                quotas[app_env.environment]["cpu_total"] += (
                    _specs["resource_limit_quota"]['cpu'] * _specs['target_replicas']
                )

        # cpu 的单位从默认的 m 转为 核
        cpu = sum([v["cpu_total"] for v in quotas.values()]) // 1000
        # 内存的单位从默认的 Mi 转为 G
        memory = sum([v["memory_total"] for v in quotas.values()]) // 1024
        return {"cpu": cpu, "memory": memory}
