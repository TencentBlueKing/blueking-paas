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

"""Config variables related functions"""

import logging
from typing import TYPE_CHECKING, Dict, Iterator, List

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.accessories.publish.entrance.preallocated import get_bk_doc_url_prefix
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.core.region.app import BuiltInEnvsRegionHelper, BuiltInEnvVarDetail
from paasng.core.region.models import get_region
from paasng.infras.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.models import get_svc_disc_as_env_variables
from paasng.platform.engine.configurations.ingress import AppDefaultDomains, AppDefaultSubpaths
from paasng.platform.engine.configurations.provider import env_vars_providers
from paasng.platform.engine.constants import AppInfoBuiltinEnv, AppRunTimeBuiltinEnv, ConfigVarEnvName
from paasng.platform.engine.models.config_var import add_prefix_to_key, get_config_vars, get_custom_builtin_config_vars
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.utils.blobstore import make_blob_store_env

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application
    from paasng.platform.engine.models import EngineApp

logger = logging.getLogger(__name__)


def get_env_variables(
    env: ModuleEnvironment,
    include_config_vars: bool = True,
    include_preset_env_vars: bool = True,
    include_svc_disc: bool = True,
) -> Dict[str, str]:
    """Get env vars for current environment, this will include:

    - env vars from services
    - user defined config vars
    - built-in env vars
    - (optional) vars defined by deployment description file

    :param include_config_vars: if True, will add envs defined in ConfigVar models to result
    :param include_preset_env_vars: if True, will add preset env vars defined in PresetEnvVariable models to result
    :param include_svc_disc: if True, will add svc discovery as env vars to result
    :returns: Dict of env vars

    ---
    for cloud native application, should not include config_var, preset_env_vars and svc_disc.
    Because these are already provided via `ManifestConstructor`
    """
    result = {}
    engine_app = env.get_engine_app()

    # Part: Gather values from registered env variables providers, it has lowest priority
    result.update(env_vars_providers.gather(env))
    if include_preset_env_vars:
        result.update(get_preset_env_variables(env))
    if include_svc_disc:
        result.update(get_svc_disc_as_env_variables(env))

    # Part: system-wide env vars
    result.update(get_builtin_env_variables(engine_app, settings.CONFIGVAR_SYSTEM_PREFIX))

    # Port: workloads related env vars
    vars_wl = _flatten_envs(generate_wl_builtin_env_vars(settings.CONFIGVAR_SYSTEM_PREFIX, env))
    result.update(vars_wl)

    # Part: insert blobstore env vars
    if env.application.type != ApplicationType.CLOUD_NATIVE:
        result.update(generate_blobstore_env_vars(engine_app))

    # Part: user defined env vars
    # Q: Why don't we use engine_app directly to get ConfigVars?
    #
    # Because Config Vars, unlike ServiceInstance, is not bind to EngineApp. It
    # has application global type which shares under every engine_app/environment of an
    # application.
    if include_config_vars:
        result.update(get_config_vars(engine_app.env.module, engine_app.env.environment))

    # Part: env vars shared from other modules
    result.update(ServiceSharingManager(env.module).get_env_variables(env, True))

    # Part: env vars provided by services
    result.update(mixed_service_mgr.get_env_vars(engine_app, filter_enabled=True))

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


def generate_env_vars_by_region_and_env(
    region: str, environment: str, config_vars_prefix: str
) -> List[BuiltInEnvVarDetail]:
    """Generate the platform address in the bk system by region and env"""
    # 需要按 region、env 写入不同值的变量
    region_related_envs = {
        "REMOTE_STATIC_URL": {"description": _("平台提供的静态资源地址前缀，不推荐使用")},
        "LOGIN_URL": {"description": _("蓝鲸统一登录访问地址")},
        "LOGIN_DOMAIN": {"description": _("蓝鲸统一登录服务域名")},
        "APIGW_OAUTH_API_URL": {"description": _("蓝鲸 APIGW 提供的 OAuth 服务，不推荐使用")},
        "COMPONENT_API_URL": {"description": _("蓝鲸的组件 API 访问地址, 给SAAS使用")},
    }
    region_envs_with_prefix = BuiltInEnvsRegionHelper(
        region_name=region,
        app_env=environment,
        required_env_dict=region_related_envs,
        prefix=config_vars_prefix,
    ).get_envs()

    # 不需要添加前缀的变量
    region_related_envs_without_prefix = {
        "BK_COMPONENT_API_URL": {"description": _("组件 API 访问地址")},
    }
    region_envs_without_prefix = BuiltInEnvsRegionHelper(
        region_name=region,
        app_env=environment,
        required_env_dict=region_related_envs_without_prefix,
    ).get_envs()

    # 微信内显示应用的静态资源地址前缀，从 PaaS2.0 上迁移过来的应用可能会用到
    weixin_url = settings.BKPAAS_WEIXIN_URL_MAP.get(environment)
    region_envs_with_prefix.extend(
        [
            BuiltInEnvVarDetail(
                key="WEIXIN_URL",
                value=weixin_url,
                description=_("应用移动端访问地址，不推荐使用"),
                prefix=config_vars_prefix,
            ),
            BuiltInEnvVarDetail(
                key="WEIXIN_REMOTE_STATIC_URL",
                value=f"{weixin_url}/static_api/",
                description=_("应用移动端静态资源地址前缀，不推荐使用"),
                prefix=config_vars_prefix,
            ),
        ]
    )

    # 不需要写入兼容性的环境变量，则直接返回
    region_container = get_region(region)
    if not region_container.provide_env_vars_platform:
        return region_envs_with_prefix + region_envs_without_prefix

    region_envs_with_prefix.extend(
        [
            # 私有化版本目前 SaaS 用到了该环境变量，需要推动切换到 BKPAAS_LOGIN_URL 这个环境变量
            BuiltInEnvVarDetail(
                key="BK_LOGIN_URL",
                value=settings.LOGIN_FULL,
                description=_("蓝鲸统一登录访问地址，建议切换为 BKPAAS_LOGIN_URL"),
            )
        ]
    )
    for paas2_env_key, paas2_env_data in settings.BK_PAAS2_PLATFORM_ENVS.items():
        region_envs_with_prefix.append(
            BuiltInEnvVarDetail(
                key=paas2_env_key, value=paas2_env_data["value"], description=paas2_env_data["description"]
            )
        )

    return region_envs_with_prefix + region_envs_without_prefix


def generate_env_vars_for_bk_platform(config_vars_prefix: str) -> List[BuiltInEnvVarDetail]:
    """Generate the platform address in the bk system"""
    system_envs_with_prefix: List[BuiltInEnvVarDetail] = [
        BuiltInEnvVarDetail(
            key="BK_DOMAIN",
            value=settings.BK_DOMAIN,
            description=_("蓝鲸根域，用于获取登录票据、国际化语言等 cookie 信息"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="URL", value=settings.BKPAAS_URL, description=_("蓝鲸PaaS平台访问URL"), prefix=config_vars_prefix
        ),
        BuiltInEnvVarDetail(
            key="CONSOLE_URL",
            value=settings.BK_CONSOLE_URL,
            description=_("蓝鲸桌面访问地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="CC_URL", value=settings.BK_CC_URL, description=_("蓝鲸配置平台访问地址"), prefix=config_vars_prefix
        ),
        BuiltInEnvVarDetail(
            key="JOB_URL", value=settings.BK_JOB_URL, description=_("蓝鲸作业平台访问地址"), prefix=config_vars_prefix
        ),
        BuiltInEnvVarDetail(
            key="IAM_URL", value=settings.BK_IAM_URL, description=_("蓝鲸权限中心访问地址"), prefix=config_vars_prefix
        ),
        BuiltInEnvVarDetail(
            key="USER_URL",
            value=settings.BK_USER_URL,
            description=_("蓝鲸用户管理访问地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="MONITORV3_URL",
            value=settings.BK_MONITORV3_URL,
            description=_("蓝鲸监控平台访问地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="LOG_URL", value=settings.BK_LOG_URL, description=_("蓝鲸日志平台访问地址"), prefix=config_vars_prefix
        ),
        BuiltInEnvVarDetail(
            key="REPO_URL", value=settings.BK_REPO_URL, description=_("蓝鲸制品库访问地址"), prefix=config_vars_prefix
        ),
        BuiltInEnvVarDetail(
            key="CI_URL",
            value=settings.BK_CI_URL,
            description=_("蓝鲸持续集成平台（蓝盾）访问地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="CODECC_URL",
            value=settings.BK_CODECC_URL,
            description=_("蓝鲸代码检查平台访问地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="TURBO_URL",
            value=settings.BK_TURBO_URL,
            description=_("蓝鲸编译加速平台访问地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="PIPELINE_URL",
            value=settings.BK_PIPELINE_URL,
            description=_("蓝鲸流水线访问地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="NODEMAN_URL",
            value=settings.BK_NODEMAN_URL,
            description=_("蓝鲸节点管理平台地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="BCS_URL",
            value=settings.BK_BCS_URL,
            description=_("蓝鲸容器管理平台地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="BSCP_URL",
            value=settings.BK_BSCP_URL,
            description=_("蓝鲸服务配置中心地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="AUDIT_URL",
            value=settings.BK_AUDIT_URL,
            description=_("蓝鲸审计中心地址"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="SHARED_RES_URL",
            value=settings.BK_SHARED_RES_URL,
            description=_("蓝鲸产品 title/footer/name/logo 等资源自定义配置的路径"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(
            key="BK_CRYPTO_TYPE",
            value=settings.BK_CRYPTO_TYPE,
            description=_("加密数据库内容的推荐算法有：SHANGMI（对应 SM4CTR 算法）和 CLASSIC（对应 Fernet 算法）"),
            prefix=config_vars_prefix,
        ),
    ]
    # 兼容私有化版本保留的 BK_ 前缀的环境变量
    system_envs_with_prefix.extend(
        [
            BuiltInEnvVarDetail(
                key="BK_API_URL_TMPL", value=settings.BK_API_URL_TMPL, description=_("网关 API 访问地址模板")
            ),
            BuiltInEnvVarDetail(
                key="BK_COMPONENT_API_URL", value=settings.BK_COMPONENT_API_URL, description=_("组件 API 访问地址")
            ),
            BuiltInEnvVarDetail(
                key="BK_PAAS2_URL", value=settings.BK_PAAS2_URL, description=_("PaaS2.0 开发者中心地址")
            ),
        ]
    )
    return system_envs_with_prefix


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
    bk_address_envs = _flatten_envs(generate_env_vars_for_bk_platform(config_vars_prefix))

    environment = engine_app.env.environment
    region = engine_app.region
    # 需要根据 region、env 写入不同值的系统环境变量
    envs_by_region_and_env = _flatten_envs(
        generate_env_vars_by_region_and_env(region, environment, config_vars_prefix)
    )

    # admin42 中自定义的环境变量
    custom_envs = get_custom_builtin_config_vars(config_vars_prefix)

    envs = {
        **app_info_envs,
        **runtime_envs,
        **bk_address_envs,
        **envs_by_region_and_env,
        "BK_DOCS_URL_PREFIX": get_bk_doc_url_prefix(),
    }

    for key, value in custom_envs.items():
        if key in envs:
            logger.warning(
                f"{key}={envs[key]} is already defined in default builtin envs, "
                f"will be overwritten by {key}={value} defined in custom builtin envs"
            )
        envs[key] = value

    return envs


# '{bk_var_*}' is a special placeholder and will be replaced by the actual value
# when the workloads resources are created.
_bk_var_tmpl_process_type = "{{bk_var_process_type}}"


def generate_wl_builtin_env_vars(config_vars_prefix: str, env=None) -> List[BuiltInEnvVarDetail]:
    """Generate env vars related with workloads.

    :param config_vars_prefix: The prefix of the env vars.
    :param env: Optional, the env object, if given, will include the env vars related
        to the environment, such as subpath, process type, etc.
    """
    items = [
        BuiltInEnvVarDetail(
            key="APP_LOG_PATH",
            value=settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR,
            description=_("应用日志文件存放路径"),
            prefix=config_vars_prefix,
        ),
        BuiltInEnvVarDetail(key="PORT", value=str(settings.CONTAINER_PORT), description=_("目标端口号，值为 5000")),
    ]
    # Extend the env vars related to the env when given
    if env:
        wl_app = env.wl_app
        app = env.module.application
        items += [
            BuiltInEnvVarDetail(
                key="LOG_NAME_PREFIX",
                value=f"{app.region}-bkapp-{app.code}-{env.environment}-{_bk_var_tmpl_process_type}",
                description=_("日志文件推荐使用的前缀"),
                prefix=config_vars_prefix,
            ),
            BuiltInEnvVarDetail(
                key="PROCESS_TYPE",
                value=_bk_var_tmpl_process_type,
                description=_("[不推荐使用] 当前进程类型"),
                prefix=config_vars_prefix,
            ),
            BuiltInEnvVarDetail(
                key="SUB_PATH",
                value=f"/{wl_app.region}-{wl_app.name}/",
                description=_("[不推荐使用] 基于规则拼接的应用访问子路径，仅适合向前兼容时使用"),
                prefix=config_vars_prefix,
            ),
        ]
    return items


def get_preset_env_variables(env: ModuleEnvironment) -> Dict[str, str]:
    """Get PresetEnvVariable as env variables dict"""
    qs: Iterator[PresetEnvVariable] = PresetEnvVariable.objects.filter(module=env.module)
    return {item.key: item.value for item in qs if item.is_within_scope(ConfigVarEnvName(env.environment))}


def _flatten_envs(nested_env_list: List[BuiltInEnvVarDetail]) -> Dict[str, str]:
    """将嵌套的环境变量字典转换为扁平的键值对格式

    调用前: [BuiltInEnvVarDetail(key="key1", value="value1", description="xxx"), BuiltInEnvVarDetail(key="key2", value="value2", description="xxx")]
    调用后: {"key1": "value1", "key2": "value2"}
    """
    flat_envs = {}
    for env in nested_env_list:
        flat_envs[env.key] = env.value
    return flat_envs
