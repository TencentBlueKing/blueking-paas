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
"""Config variables related functions"""
from typing import TYPE_CHECKING, Dict, Optional

from django.conf import settings

from paasng.accessories.publish.entrance.preallocated import get_bk_doc_url_prefix
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.core.region.app import BuiltInEnvsRegionHelper
from paasng.core.region.models import get_region
from paasng.infras.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.ingress import AppDefaultDomains, AppDefaultSubpaths
from paasng.platform.engine.configurations.provider import env_vars_providers
from paasng.platform.engine.constants import AppInfoBuiltinEnv, AppRunTimeBuiltinEnv
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.models.config_var import add_prefix_to_key, get_config_vars
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.utils.blobstore import make_blob_store_env

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application
    from paasng.platform.engine.models import EngineApp


def get_env_variables(
    env: ModuleEnvironment, deployment: Optional[Deployment] = None, include_config_var: bool = True
) -> Dict[str, str]:
    """Get env vars for current environment, this will include:

    - env vars from services
    - user defined config vars
    - built-in env vars
    - (optional) vars defined by deployment description file

    :param deployment: Optional deployment object to get vars defined in description file
    :param include_config_var: if include_config_var is True, will add envs defined in ConfigVar models to result
    :returns: Dict of env vars
    """
    result = {}
    engine_app = env.get_engine_app()

    # Part: Gather values from registered env variables providers, it has lowest priority
    result.update(env_vars_providers.gather(env, deployment))

    # Part: system-wide env vars
    result.update(get_builtin_env_variables(engine_app, settings.CONFIGVAR_SYSTEM_PREFIX))

    # Part: insert blobstore env vars
    if env.application.type != ApplicationType.CLOUD_NATIVE:
        result.update(generate_blobstore_env_vars(engine_app))

    # Part: user defined env vars
    # Q: Why don't we using engine_app directly to get ConfigVars?
    #
    # Because Config Vars, unlike ServiceInstance, is not bind to EngineApp. It
    # has application global type which shares under every engine_app/environment of an
    # application.
    #
    # Q: Why cnative application doesn't add user defined env vars
    #
    # Because user defined env vars have been added into BkAppSpec
    if include_config_var:
        result.update(get_config_vars(engine_app.env.module, engine_app.env.environment))

    # Part: env vars shared from other modules
    result.update(ServiceSharingManager(env.module).get_env_variables(env))

    # Part: env vars provided by services
    result.update(mixed_service_mgr.get_env_vars(engine_app))

    # Part: Application's default sub domains/paths
    result.update(AppDefaultDomains(env).as_env_vars())
    result.update(AppDefaultSubpaths(env).as_env_vars())
    return result


def generate_env_vars_for_app(app: "Application", config_vars_prefix: str) -> Dict[str, str]:
    """Generate built-in envs for app basic information"""
    # Query oauth2 client to get app secret, if the client does not exist yet, use an empty
    # string instead.
    try:
        app_secret = get_oauth2_client_secret(app.code, app.region)
    except BkOauthClientDoesNotExist:
        app_secret = ""

    app_info_envs = {
        AppInfoBuiltinEnv.APP_ID.value: app.code,
        AppInfoBuiltinEnv.APP_SECRET.value: app_secret,
        # 兼容之前的数据，不确定是否有应用使用到了 BKPAAS_APP_CODE 这个环境变量，故先保留
        "APP_CODE": app.code,
    }
    # 系统环境变量需要添加统一的前缀
    return add_prefix_to_key(app_info_envs, config_vars_prefix)


def generate_runtime_env_vars_for_app(engine_app: "EngineApp", config_vars_prefix: str) -> Dict[str, str]:
    """Generate built-in  runtime envs for app"""
    runtime_envs = {
        AppRunTimeBuiltinEnv.APP_MODULE_NAME.value: engine_app.env.module.name,
        AppRunTimeBuiltinEnv.ENVIRONMENT.value: engine_app.env.environment,
        AppRunTimeBuiltinEnv.MAJOR_VERSION.value: 3,
        AppRunTimeBuiltinEnv.ENGINE_REGION.value: engine_app.region,
        # 这几个变量用户很少使用，暂不展示描述信息到页面上
        "ENGINE_APP_NAME": engine_app.name,
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
    envs["WEIXIN_URL"] = weixin_url
    envs["WEIXIN_REMOTE_STATIC_URL"] = f"{weixin_url}/static_api/"

    # 系统环境变量需要添加统一的前缀
    envs_dict = add_prefix_to_key(envs, config_vars_prefix)

    # 不需要写入兼容性的环境变量，则直接返回
    region_container = get_region(region)
    if not region_container.provide_env_vars_platform:
        return envs_dict

    bk_envs = {
        # 私有化版本目前 SaaS 用到了该环境变量，需要推动切换到 BKPAAS_LOGIN_URL 这个环境变量
        "BK_LOGIN_URL": settings.LOGIN_FULL,
    }
    bk_envs.update(settings.BK_PLATFORM_URLS)
    return {**envs_dict, **bk_envs}


def generate_env_vars_for_bk_platform(config_vars_prefix: str) -> Dict[str, str]:
    """Generate the platform address in the bk system"""

    system_envs = {
        "BK_CRYPTO_TYPE": settings.BK_CRYPTO_TYPE,
        "BK_DOMAIN": settings.BK_DOMAIN,
        "URL": settings.BKPAAS_URL,
        # 蓝鲸桌面地址
        "CONSOLE_URL": settings.BK_CONSOLE_URL,
        # 蓝鲸体系内产品地址
        "CC_URL": settings.BK_CC_URL,
        "JOB_URL": settings.BK_JOB_URL,
        "IAM_URL": settings.BK_IAM_URL,
        "USER_URL": settings.BK_USER_URL,
        "MONITORV3_URL": settings.BK_MONITORV3_URL,
        "LOG_URL": settings.BK_LOG_URL,
        "REPO_URL": settings.BK_REPO_URL,
        "CI_URL": settings.BK_CI_URL,
        "CODECC_URL": settings.BK_CODECC_URL,
        "TURBO_URL": settings.BK_TURBO_URL,
        "PIPELINE_URL": settings.BK_PIPELINE_URL,
    }
    # 系统环境变量需要添加统一的前缀
    system_envs_dict = add_prefix_to_key(system_envs, config_vars_prefix)
    # 兼容私有化版本保留的 BK_ 前缀的环境变量
    system_envs_dict["BK_API_URL_TMPL"] = settings.BK_API_URL_TMPL
    system_envs_dict["BK_COMPONENT_API_URL"] = settings.BK_COMPONENT_API_URL
    system_envs_dict["BK_PAAS2_URL"] = settings.BK_PAAS2_URL

    return system_envs_dict


def generate_blobstore_env_vars(engine_app: "EngineApp") -> Dict[str, str]:
    """Generate blobstore env vars by engine_app"""
    m = ModuleRuntimeManager(engine_app.env.module)
    if not m.is_need_blobstore_env:
        return {}
    return make_blob_store_env(encrypt=m.is_secure_encrypted_runtime)


def get_builtin_env_variables(engine_app: "EngineApp", config_vars_prefix: str) -> Dict[str, str]:
    """Get all platform built-in env vars"""
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

    return {
        **app_info_envs,
        **runtime_envs,
        **bk_address_envs,
        **envs_by_region_and_env,
        "BK_DOCS_URL_PREFIX": get_bk_doc_url_prefix(),
    }
