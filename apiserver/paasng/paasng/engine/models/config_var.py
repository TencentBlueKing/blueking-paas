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
from typing import TYPE_CHECKING, Dict

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from paasng.engine.constants import AppInfoBuiltinEnv, AppRunTimeBuiltinEnv, ConfigVarEnvName
from paasng.platform.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.platform.oauth2.utils import get_oauth2_client_secret
from paasng.platform.region.app import BuiltInEnvsRegionHelper
from paasng.platform.region.models import get_region
from paasng.utils.blobstore import make_blob_store_env
from paasng.utils.models import TimestampedModel

if TYPE_CHECKING:
    from paasng.engine.models import EngineApp
    from paasng.platform.applications.models import Application
    from paasng.platform.modules.models.module import Module

ENVIRONMENT_ID_FOR_GLOBAL = -1
ENVIRONMENT_NAME_FOR_GLOBAL = ConfigVarEnvName.GLOBAL.value


def get_config_vars(module, env_name):
    """Get ConfigVars of module as dict, config vars priority: builtin/not global/global

    :param str env_name: environment name, such as 'prod'
    :returns: Dict of config vars
    """
    try:
        env_id = module.envs.get(environment=env_name).pk
    except ObjectDoesNotExist:
        raise ValueError('Invalid env_name given: %s' % env_name)

    config_vars = ConfigVar.objects.filter(
        module=module, environment_id__in=(ENVIRONMENT_ID_FOR_GLOBAL, env_id)
    ).order_by('environment_id')
    return {obj.key: obj.value for obj in config_vars}


class ConfigVarQuerySet(models.QuerySet):
    """Custom QuerySet for ConfigVar model"""

    def filter_by_environment_name(self, name: ConfigVarEnvName):
        """Filter ConfigVar objects by environment name"""
        if name == ConfigVarEnvName.GLOBAL:
            return self.filter(environment_id=ENVIRONMENT_ID_FOR_GLOBAL)
        return self.filter(environment__environment=name.value)


class ConfigVar(TimestampedModel):
    """Config vars for application"""

    module = models.ForeignKey('modules.Module', on_delete=models.CASCADE, null=True)

    is_global = models.BooleanField(default=False)
    # When is_global is True, environment_id will be set to -1, because null value will break
    # MySQL unique index, see: https://stackoverflow.com/questions/1346765/unique-constraint-that-allows-empty-values-in-mysql # noqa
    environment = models.ForeignKey(
        'applications.ApplicationEnvironment', on_delete=models.CASCADE, db_constraint=False, null=True
    )

    key = models.CharField(max_length=128, null=False)
    value = models.TextField(null=False)
    description = models.CharField(max_length=200, null=True)
    is_builtin = models.BooleanField(default=False)

    objects = ConfigVarQuerySet.as_manager()

    class Meta:
        unique_together = ('module', 'is_global', 'environment', 'key')

    def __str__(self):
        return "{var_name}-{var_value}-{app_code}".format(
            var_name=self.key, var_value=self.value, app_code=self.module.application.code
        )

    @property
    def environment_name(self):
        if self.environment_id == ENVIRONMENT_ID_FOR_GLOBAL:
            return ConfigVarEnvName.GLOBAL.value
        return ConfigVarEnvName(self.environment.environment).value

    def is_equivalent_to(self, other: 'ConfigVar') -> bool:
        """Determine whether the two ConfigVars are equivalent.

        Equivalent is meaning that the tow quadruple(key, value, description, environment_name) are all equal.

        :param other: the other ConfigVar
        :return: are equivalent or not
        """
        return (self.key, self.value, self.description, self.environment_name) == (
            other.key,
            other.value,
            other.description,
            self.environment_name,
        )

    def clone_to(self, module: 'Module') -> 'ConfigVar':
        """Make a copy ConfigVar, but linking to the module in params."""
        if self.environment_id == ENVIRONMENT_ID_FOR_GLOBAL:
            environment_id = ENVIRONMENT_ID_FOR_GLOBAL
        else:
            environment_id = module.get_envs(self.environment.environment).id

        return ConfigVar(
            key=self.key,
            value=self.value,
            description=self.description,
            is_global=self.is_global,
            is_builtin=self.is_builtin,
            # 差异点
            environment_id=environment_id,
            module=module,
        )


def generate_blobstore_env_vars(engine_app: 'EngineApp') -> Dict[str, str]:
    """Generate blobstore env vars by engine_app"""
    from paasng.platform.modules.helpers import ModuleRuntimeManager

    m = ModuleRuntimeManager(engine_app.env.module)
    if not m.is_need_blobstore_env:
        return {}
    return make_blob_store_env(encrypt=m.is_secure_encrypted_runtime)


def add_prefix_to_key(items: dict, prefix: str) -> Dict[str, str]:
    return {f"{prefix}{key}": value for key, value in items.items()}


def generate_env_vars_for_app(app: 'Application', config_vars_prefix: str) -> Dict[str, str]:
    """Generate built-in envs for app basic information"""
    # Query oauth2 client to get app secret, if the client does not exist yet, use an empty
    # string instead.
    try:
        app_secret = get_oauth2_client_secret(app.code, app.region)
    except BkOauthClientDoesNotExist:
        app_secret = ''

    app_info_envs = {
        AppInfoBuiltinEnv.APP_ID.value: app.code,
        AppInfoBuiltinEnv.APP_SECRET.value: app_secret,
        # 兼容之前的数据，不确定是否有应用使用到了 BKPAAS_APP_CODE 这个环境变量，故先保留
        'APP_CODE': app.code,
    }
    # 系统环境变量需要添加统一的前缀
    return add_prefix_to_key(app_info_envs, config_vars_prefix)


def generate_runtime_env_vars_for_app(engine_app: 'Application', config_vars_prefix: str) -> Dict[str, str]:
    """Generate built-in  runtime envs for app"""
    runtime_envs = {
        AppRunTimeBuiltinEnv.APP_MODULE_NAME.value: engine_app.env.module.name,
        AppRunTimeBuiltinEnv.ENVIRONMENT.value: engine_app.env.environment,
        AppRunTimeBuiltinEnv.MAJOR_VERSION.value: 3,
        AppRunTimeBuiltinEnv.ENGINE_REGION.value: engine_app.region,
        # 这几个变量用户很少使用，暂不展示描述信息到页面上
        'ENGINE_APP_NAME': engine_app.name,
    }
    return add_prefix_to_key(runtime_envs, config_vars_prefix)


def generate_env_vars_by_region_and_env(region: str, environment: str, config_vars_prefix: str) -> Dict[str, str]:
    """Generate the platform address in the bk system by region and env"""
    # 需要按 region、env 写入不同值的变量
    region_related_envs = ["REMOTE_STATIC_URL", "LOGIN_URL", "LOGIN_DOMAIN", "APIGW_OAUTH_API_URL"]
    envs = BuiltInEnvsRegionHelper(
        region_name=region, app_env=environment, env_key_list=region_related_envs
    ).get_envs()

    # 微信内显示应用的静态资源地址前缀，从 PaaS2.0 上迁移过来的应用可能会用到
    weixin_url = settings.BKPAAS_WEIXIN_URL_MAP.get(environment)
    envs['WEIXIN_URL'] = weixin_url
    envs['WEIXIN_REMOTE_STATIC_URL'] = f'{weixin_url}/static_api/'

    # 系统环境变量需要添加统一的前缀
    envs_dict = add_prefix_to_key(envs, config_vars_prefix)

    # 不需要写入兼容性的环境变量，则直接返回
    region_container = get_region(region)
    if not region_container.provide_env_vars_platform:
        return envs_dict

    bk_envs = {
        # 私有化版本目前 SaaS 用到了该环境变量，需要推动切换到 BKPAAS_LOGIN_URL 这个环境变量
        'BK_LOGIN_URL': settings.LOGIN_FULL,
    }
    bk_envs.update(settings.BK_PLATFORM_URLS)
    return {**envs_dict, **bk_envs}


def generate_env_vars_for_bk_platform(config_vars_prefix: str) -> Dict[str, str]:
    """Generate the platform address in the bk system"""

    system_envs = {
        'URL': settings.BKPAAS_URL,
        # 蓝鲸桌面地址
        'CONSOLE_URL': settings.BK_CONSOLE_URL,
        # 蓝鲸体系内产品地址
        'CC_URL': settings.BK_CC_URL,
        'JOB_URL': settings.BK_JOB_URL,
        'IAM_URL': settings.BK_IAM_URL,
        'USER_URL': settings.BK_USER_URL,
        'MONITORV3_URL': settings.BK_MONITORV3_URL,
        'LOG_URL': settings.BK_LOG_URL,
        'REPO_URL': settings.BK_REPO_URL,
        'CI_URL': settings.BK_CI_URL,
        'CODECC_URL': settings.BK_CODECC_URL,
        'TURBO_URL': settings.BK_TURBO_URL,
        'PIPELINE_URL': settings.BK_PIPELINE_URL,
    }
    # 系统环境变量需要添加统一的前缀
    system_envs_dict = add_prefix_to_key(system_envs, config_vars_prefix)
    # 兼容私有化版本保留的 BK_ 前缀的环境变量
    system_envs_dict['BK_API_URL_TMPL'] = settings.BK_API_URL_TMPL
    system_envs_dict['BK_COMPONENT_API_URL'] = settings.BK_COMPONENT_API_URL
    system_envs_dict['BK_PAAS2_URL'] = settings.BK_PAAS2_URL

    return system_envs_dict


def generate_builtin_env_vars(engine_app: 'EngineApp', config_vars_prefix: str) -> Dict[str, str]:
    """Generate platform built-in env vars"""
    app = engine_app.env.application
    # 应用基本信息环境变量
    app_info_envs = generate_env_vars_for_app(app, config_vars_prefix)

    # 应用运行时环境变量
    runtime_envs = generate_runtime_env_vars_for_app(engine_app, config_vars_prefix)

    # 蓝鲸体系内平台的访问地址
    bk_address_envs = generate_env_vars_for_bk_platform(config_vars_prefix)

    environment = engine_app.env.environment
    region = engine_app.region
    # 需要根据 region、env 写入不同值的系统环境变量
    envs_by_region_and_env = generate_env_vars_by_region_and_env(region, environment, config_vars_prefix)

    return {**app_info_envs, **runtime_envs, **bk_address_envs, **envs_by_region_and_env}
