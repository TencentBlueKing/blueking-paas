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
from paasng.core.region.app import BuiltInEnvsRegionHelper
from paasng.core.region.models import get_region
from paasng.infras.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.env_var import listers as vars_listers
from paasng.platform.engine.configurations.env_var.entities import EnvVariableList, EnvVariableObj
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.config_var import BuiltinConfigVar
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


def sys_var(key: str, value: str, description: str | None) -> EnvVariableObj:
    """A shortcut function to create a system environment variable object, it helps to make the
    code more succinct."""
    return EnvVariableObj.with_sys_prefix(key=key, value=value, description=description)


def list_vars_builtin_app_basic(app: "Application", include_deprecated: bool = True) -> EnvVariableList:
    """List app basic information related built-in envs.

    :param include_deprecated: Whether to include the "deprecated" ones, when displaying to
        the users, set this to False.
    """
    # Query oauth2 client to get app secret, if the client does not exist yet, use an empty
    # string instead.
    try:
        app_secret = get_oauth2_client_secret(app.code)
    except BkOauthClientDoesNotExist:
        app_secret = ""

    results = EnvVariableList(
        [
            sys_var("APP_ID", app.code, _("蓝鲸应用ID")),
            sys_var("APP_SECRET", app_secret, _("蓝鲸应用密钥")),
            sys_var("APP_TENANT_ID", app.app_tenant_id, _("蓝鲸应用租户 ID")),
        ]
    )
    if include_deprecated:
        results.append(
            # 兼容之前的数据，不确定是否有应用使用到了 BKPAAS_APP_CODE 这个环境变量，故先保留
            sys_var("APP_CODE", app.code, _("[不推荐使用] 应用 Code，历史变量因兼容性保留")),
        )
    return results


def list_vars_builtin_region(region: str, environment: str) -> EnvVariableList:
    """List region related builtin env vars.

    :param region: The region name.
    :param environment: The environment name, such as "stag" or "prod".
    """
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
        required_env_dict=region_related_envs,
    ).get_envs()

    # 微信内显示应用的静态资源地址前缀，从 PaaS2.0 上迁移过来的应用可能会用到
    weixin_url = settings.BKPAAS_WEIXIN_URL_MAP.get(environment)
    region_envs_with_prefix.extend(
        [
            sys_var("WEIXIN_URL", weixin_url, _("应用移动端访问地址，不推荐使用")),
            sys_var(
                "WEIXIN_REMOTE_STATIC_URL", f"{weixin_url}/static_api/", _("应用移动端静态资源地址前缀，不推荐使用")
            ),
        ]
    )

    # 不需要写入兼容性的环境变量，则直接返回
    region_container = get_region(region)
    if not region_container.provide_env_vars_platform:
        return EnvVariableList(region_envs_with_prefix)

    region_envs_with_prefix.extend(
        [
            # 私有化版本目前 SaaS 用到了该环境变量，需要推动切换到 BKPAAS_LOGIN_URL 这个环境变量
            EnvVariableObj(
                key="BK_LOGIN_URL",
                value=settings.LOGIN_FULL,
                description=_("蓝鲸统一登录访问地址，建议切换为 BKPAAS_LOGIN_URL"),
            )
        ]
    )
    for paas2_env_key, paas2_env_data in settings.BK_PAAS2_PLATFORM_ENVS.items():
        region_envs_with_prefix.append(
            EnvVariableObj(key=paas2_env_key, value=paas2_env_data["value"], description=paas2_env_data["description"])
        )
    return EnvVariableList(region_envs_with_prefix)


def list_vars_builtin_plat_addrs() -> EnvVariableList:
    """List the platform address builtin env vars."""
    # 环境变量中的 bool 值需要转为小写开头字符串，"true" 表示开启，"false" 表示不开启
    multi_tenant_mode = "true" if settings.ENABLE_MULTI_TENANT_MODE else "false"
    system_envs_with_prefix = [
        sys_var("BK_DOMAIN", settings.BK_DOMAIN, _("蓝鲸根域，用于获取登录票据、国际化语言等 cookie 信息")),
        sys_var("URL", settings.BKPAAS_URL, _("蓝鲸PaaS平台访问URL")),
        sys_var("CONSOLE_URL", settings.BK_CONSOLE_URL, _("蓝鲸桌面访问地址")),
        sys_var("CC_URL", settings.BK_CC_URL, _("蓝鲸配置平台访问地址")),
        sys_var("JOB_URL", settings.BK_JOB_URL, _("蓝鲸作业平台访问地址")),
        sys_var("IAM_URL", settings.BK_IAM_URL, _("蓝鲸权限中心访问地址")),
        sys_var("USER_URL", settings.BK_USER_URL, _("蓝鲸用户管理访问地址")),
        sys_var("MONITORV3_URL", settings.BK_MONITORV3_URL, _("蓝鲸监控平台访问地址")),
        sys_var("LOG_URL", settings.BK_LOG_URL, _("蓝鲸日志平台访问地址")),
        sys_var("REPO_URL", settings.BK_REPO_URL, _("蓝鲸制品库访问地址")),
        sys_var("CI_URL", settings.BK_CI_URL, _("蓝鲸持续集成平台（蓝盾）访问地址")),
        sys_var("CODECC_URL", settings.BK_CODECC_URL, _("蓝鲸代码检查平台访问地址")),
        sys_var("TURBO_URL", settings.BK_TURBO_URL, _("蓝鲸编译加速平台访问地址")),
        sys_var("PIPELINE_URL", settings.BK_PIPELINE_URL, _("蓝鲸流水线访问地址")),
        sys_var("NODEMAN_URL", settings.BK_NODEMAN_URL, _("蓝鲸节点管理平台地址")),
        sys_var("BCS_URL", settings.BK_BCS_URL, _("蓝鲸容器管理平台地址")),
        sys_var("BSCP_URL", settings.BK_BSCP_URL, _("蓝鲸服务配置中心地址")),
        sys_var("AUDIT_URL", settings.BK_AUDIT_URL, _("蓝鲸审计中心地址")),
        sys_var(
            "SHARED_RES_URL", settings.BK_SHARED_RES_URL, _("蓝鲸产品 title/footer/name/logo 等资源自定义配置的路径")
        ),
        sys_var(
            "BK_CRYPTO_TYPE",
            settings.BK_CRYPTO_TYPE,
            _("加密数据库内容的推荐算法有：SHANGMI（对应 SM4CTR 算法）和 CLASSIC（对应 Fernet 算法）"),
        ),
        sys_var("MULTI_TENANT_MODE", multi_tenant_mode, _("是否开启多租户模式")),
    ]
    # 兼容私有化版本保留的 BK_ 前缀的环境变量
    system_envs_with_prefix.extend(
        [
            EnvVariableObj(
                key="BK_API_URL_TMPL", value=settings.BK_API_URL_TMPL, description=_("网关 API 访问地址模板")
            ),
            EnvVariableObj(
                key="BK_COMPONENT_API_URL", value=settings.BK_COMPONENT_API_URL, description=_("组件 API 访问地址")
            ),
            EnvVariableObj(key="BK_PAAS2_URL", value=settings.BK_PAAS2_URL, description=_("PaaS2.0 开发者中心地址")),
        ]
    )
    return EnvVariableList(system_envs_with_prefix)


def get_builtin_env_variables(engine_app: "EngineApp") -> EnvVariableList:
    """Get all platform built-in env vars"""
    app = engine_app.env.application
    env = engine_app.env

    result = EnvVariableList()
    # 应用基本信息环境变量
    result.extend(list_vars_builtin_app_basic(app))

    # 蓝鲸体系内平台的访问地址
    result.extend(list_vars_builtin_plat_addrs())

    # 需要根据 region、env 写入不同值的系统环境变量
    result.extend(list_vars_builtin_region(app.region, env.environment))

    # 蓝鲸文档地址前缀
    result.append(EnvVariableObj(key="BK_DOCS_URL_PREFIX", value=get_bk_doc_url_prefix(), description=""))

    # admin42 中自定义的环境变量
    custom_sys_envs = get_custom_builtin_config_vars()
    # 如果自定义的系统内置变量有冲突，打印出来
    custom_sys_kv, result_kv = custom_sys_envs.kv_map, result.kv_map
    for key in set(custom_sys_kv.keys()) & set(result_kv.keys()):
        logger.warning(
            f"{key}={result_kv[key]} is already defined in default builtin envs, "
            f"will be overwritten by {key}={custom_sys_kv[key]} defined in custom builtin envs"
        )
    result.extend(custom_sys_envs)

    # 应用运行时相关环境变量
    result.extend(list_vars_builtin_runtime(env))
    return result


# '{bk_var_*}' is a special placeholder and will be replaced by the actual value
# when the workloads resources are created.
_bk_var_tmpl_process_type = "{{bk_var_process_type}}"


def list_vars_builtin_runtime(env: ModuleEnvironment, include_deprecated: bool = True) -> EnvVariableList:
    """Generate env vars related with workloads.

    :param env: the env object.
    :param include_deprecated: Whether to include deprecated variables.
    """
    app = env.module.application
    engine_app = env.get_engine_app()
    wl_app = env.wl_app
    items = [
        sys_var("APP_MODULE_NAME", env.module.name, _("应用当前模块名")),
        sys_var("ENVIRONMENT", env.environment, _("应用当前环境，预发布环境为 stag、生产环境为 prod")),
        sys_var("MAJOR_VERSION", str(3), _("应用当前运行的开发者中心版本，值为 3")),
        sys_var("ENGINE_REGION", env.region, _("应用版本，默认版本为 default")),
        sys_var("APP_LOG_PATH", settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR, _("应用日志文件存放路径")),
        EnvVariableObj(key="PORT", value=str(settings.CONTAINER_PORT), description=_("目标端口号，值为 5000")),
    ]
    if include_deprecated:
        # 这几个变量用户很少使用，暂不展示描述信息到页面上
        items.extend(
            [
                sys_var("ENGINE_APP_NAME", engine_app.name, _("[不推荐使用] 内部变量，不推荐使用")),
                sys_var(
                    "LOG_NAME_PREFIX",
                    f"{app.region}-bkapp-{app.code}-{env.environment}-{_bk_var_tmpl_process_type}",
                    _("日志文件推荐使用的前缀"),
                ),
                sys_var("PROCESS_TYPE", _bk_var_tmpl_process_type, _("[不推荐使用] 当前进程类型")),
                sys_var(
                    "SUB_PATH",
                    f"/{wl_app.region}-{wl_app.name}/",
                    _("[不推荐使用] 基于规则拼接的应用访问子路径，仅适合向前兼容时使用"),
                ),
            ]
        )
    return EnvVariableList(items)


def get_preset_env_variables(env: ModuleEnvironment) -> Dict[str, str]:
    """Get PresetEnvVariable as env variables dict"""
    qs: Iterator[PresetEnvVariable] = PresetEnvVariable.objects.filter(module=env.module)
    return {item.key: item.value for item in qs if item.is_within_scope(ConfigVarEnvName(env.environment))}


def get_custom_builtin_config_vars() -> EnvVariableList:
    """Get the custom builtin config vars."""
    items = BuiltinConfigVar.objects.values_list("key", "value", "description")
    return EnvVariableList(sys_var(key, value, description) for key, value, description in items)
