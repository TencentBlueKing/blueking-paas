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
from enum import StrEnum
from typing import TYPE_CHECKING, Dict, Iterator, List

from attrs import define
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.accessories.publish.entrance.preallocated import get_bk_doc_url_prefix
from paasng.core.region.app import BuiltInEnvsRegionHelper, BuiltInEnvVarDetail
from paasng.core.region.models import get_region
from paasng.infras.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.env_var import listers as vars_listers
from paasng.platform.engine.configurations.env_var.listers import EnvVariableList
from paasng.platform.engine.constants import AppInfoBuiltinEnv, AppRunTimeBuiltinEnv, ConfigVarEnvName
from paasng.platform.engine.models.config_var import (
    add_prefix_to_key,
    get_custom_builtin_config_vars,
)
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.models import Module

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application
    from paasng.platform.engine.models import EngineApp

logger = logging.getLogger(__name__)


def get_env_variables(env: ModuleEnvironment) -> Dict[str, str]:
    """Get env vars for current environment, the result includes user defined and builtin env vars.

    :param env: The environment object.
    :return: A dict of env variables.
    """
    return UnifiedEnvVarsReader(env).get_kv_map()


class EnvVarSource(StrEnum):
    """Enum for environment variable sources."""

    # Sources configured by user:
    #
    # USER_PRESET source means the var was configured by the app description file.
    USER_PRESET = "user_preset"
    # USER_CONFIGURED source means the var was configured from the config var management webpage
    # or API by the user.
    USER_CONFIGURED = "user_configured"

    # Provided by the platform
    BUILTIN_BLOBSTORE = "builtin_blobstore"
    BUILTIN_MISC = "builtin_misc"
    BUILTIN_SVC_DISC = "builtin_svc_disc"
    BUILTIN_ADDONS = "builtin_addons"
    BUILTIN_DEFAULT_ENTRANCE = "builtin_default_entrance"


class UnifiedEnvVarsReader:
    """A class to merge env variables from different sources."""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

        # Register the functions in the lister module
        self._source_lister_func_map = {
            source: getattr(vars_listers, f"list_vars_{source}") for source in EnvVarSource
        }

        # The default order for merging env variables. In this order, the preset vars has lowest
        # priority and the user configured vars has higher priority and can override
        # some built-in env vars except builtin-addons and builtin-default-entrance.
        self._default_order = [
            EnvVarSource.USER_PRESET,
            EnvVarSource.BUILTIN_SVC_DISC,
            EnvVarSource.BUILTIN_MISC,
            EnvVarSource.BUILTIN_BLOBSTORE,
            EnvVarSource.USER_CONFIGURED,
            # Below builtin vars won't be touched by user
            EnvVarSource.BUILTIN_ADDONS,
            EnvVarSource.BUILTIN_DEFAULT_ENTRANCE,
        ]

    def get_kv_map(self, exclude_sources: list[EnvVarSource] | None = None) -> Dict[str, str]:
        """Get env variables in the format of {key: value} dictionary.

        :param exclude_sources: A list of sources to exclude from the result.
        :return: A dict of env variables.
        """
        env_list = EnvVariableList()
        for source in self._default_order:
            if exclude_sources and source in exclude_sources:
                continue
            env_list.extend(self._source_lister_func_map[source](self.env))
        return env_list.kv_map

    def get_user_conflicted_keys(self, exclude_sources: list[EnvVarSource] | None = None) -> "List[ConflictedKey]":
        """Get the conflicted keys. A conflicted key is a key that defined in the USER_CONFIGURED
        source, but also exists in other sources.

        :param exclude_sources: A list of sources to exclude when checking conflicts.
        :return: A list of ConflictedKey objects.
        """
        # Whether the current source being checked is after the USER_CONFIGURED source
        after_source = False
        # Get all keys defined by the user in the USER_CONFIGURED source
        user_keys = {item.key for item in self._source_lister_func_map[EnvVarSource.USER_CONFIGURED](self.env)}

        # Use a dict to store the result in case a key conflicts with multiple sources
        conflicted_keys = {}
        for current_source in self._default_order:
            # Skip all user preset source, because they will be overridden anyway so conflict checking
            # is not needed.
            if current_source == EnvVarSource.USER_PRESET:
                continue
            # Skip the source itself because it won't conflict with itself.
            if current_source == EnvVarSource.USER_CONFIGURED:
                after_source = True
                continue
            if exclude_sources and current_source in exclude_sources:
                continue

            data = self._source_lister_func_map[current_source](self.env).map
            for key in user_keys:
                if key in data:
                    conflicted_keys[key] = ConflictedKey(
                        key=key,
                        conflicted_source=current_source,
                        conflicted_detail=data[key].description,
                        override_conflicted=not after_source,
                    )

        # Sort and return the result
        return sorted(conflicted_keys.values(), key=lambda x: x.key)


def get_user_conflicted_keys(module: Module) -> "List[ConflictedKey]":
    """Get user defined config vars keys that conflict with built-in env vars, the result can be
    an useful hint for users to avoid conflicts.

    :param module: The module to check for conflicts.
    :return: List of conflicting keys.
    """
    app = module.application
    # Use a dict remove duplicated keys between different environments
    results = {}
    # Check all environments in the module and merge the results
    for env in module.get_envs():
        if app.type == ApplicationType.CLOUD_NATIVE:
            keys = UnifiedEnvVarsReader(env).get_user_conflicted_keys(
                # Exclude some sources because cloud-native apps does use them directly,
                # see `apply_builtin_env_vars()` for more details.
                exclude_sources=[
                    EnvVarSource.BUILTIN_SVC_DISC,
                    EnvVarSource.BUILTIN_BLOBSTORE,
                ],
            )
            # Any conflicted keys should not take effect because the special mechanism used for cloud-native apps
            for item in keys:
                item.override_conflicted = False

            results.update({item.key: item for item in keys})
        else:
            keys = UnifiedEnvVarsReader(env).get_user_conflicted_keys()
            results.update({item.key: item for item in keys})
    return list(results.values())


@define
class ConflictedKey:
    """A conflicted config var key object.

    :param key: The key of the config var.
    :param conflicted_source: The source of the conflict, such as "builtin_addons", "builtin_blobstore".
    :param conflicted_detail: Additional details about the conflict, if any.
    :param override_conflicted: Whether the config var key has overridden the conflicting one.
    """

    key: str
    conflicted_source: str
    override_conflicted: bool
    conflicted_detail: str | None = None


def generate_env_vars_for_app(app: "Application", config_vars_prefix: str) -> Dict[str, str]:
    """Generate built-in envs for app basic information"""
    # Query oauth2 client to get app secret, if the client does not exist yet, use an empty
    # string instead.
    try:
        app_secret = get_oauth2_client_secret(app.code)
    except BkOauthClientDoesNotExist:
        app_secret = ""

    app_info_envs = {
        AppInfoBuiltinEnv.APP_ID.value: app.code,
        AppInfoBuiltinEnv.APP_SECRET.value: app_secret,
        AppInfoBuiltinEnv.APP_TENANT_ID.value: app.app_tenant_id,
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
    }
    region_envs_with_prefix = BuiltInEnvsRegionHelper(
        region_name=region,
        app_env=environment,
        prefix=config_vars_prefix,
        required_env_dict=region_related_envs,
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
        return region_envs_with_prefix

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
    return region_envs_with_prefix


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
        BuiltInEnvVarDetail(
            key="MULTI_TENANT_MODE",
            value=settings.ENABLE_MULTI_TENANT_MODE,
            description=_("是否开启多租户模式"),
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
