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
"""PaaS Workload service settings

默认情况下，本项目会读取根目录（manage.py 所在目录）下的 `settings_files` 子目录内的所有
YAML 文件和 `settings_local.yaml` 的内容，将其作为配置项使用。你也可以用 `PAAS_WL_SETTINGS`
环境变量指定其他配置文件，比如：

    # 多个配置文件使用 ; 分割
    export PAAS_SETTINGS='common.yaml;dev.yaml'

指定其他文件后，`settings_files/*.yaml` 与 `settings_local.yaml` 仍然会生效，最终
配置会是所有内容合并后的结果。

除了 YAML 外，每个配置项也可通过环境变量设置。比如，在 YAML 文件里的配置项 `SECRET_KEY: foo`，
也可使用以下环境变量修改：

    export PAAS_WL_SECRET_KEY="foo"

注意事项：

- 必须添加 `PAAS_WL_` 前缀
- 环境变量比 YAML 配置的优先级更高
- 环境变量可修改字典内的嵌套值，参考文档：https://www.dynaconf.com/envvars/
"""
from pathlib import Path

from dynaconf import LazySettings, Validator

BASE_DIR = Path(__file__).parents[2]

SETTINGS_FILES_GLOB = str(BASE_DIR / 'settings_files/*.yaml')
LOCAL_SETTINGS = str(BASE_DIR / 'settings_local.yaml')

settings = LazySettings(
    environments=False,
    load_dotenv=True,
    # Read settings files in below locations
    includes=[SETTINGS_FILES_GLOB, LOCAL_SETTINGS],
    validators=[
        # Configure minimal required settings
        Validator('BKKRILL_ENCRYPT_SECRET_KEY', must_exist=True),
    ],
    # Envvar name configs
    # 环境变量的前缀差异化保留
    ENVVAR_PREFIX_FOR_DYNACONF="PAAS_WL",
    # 保持与 apiserver 项目一致
    ENVVAR_FOR_DYNACONF="PAAS_SETTINGS",
)


# ---------------
# 资源限制配置
# ---------------
DEFAULT_WEB_REPLICAS_MAP = settings.get('DEFAULT_WEB_REPLICAS_MAP', {'stag': 1, 'prod': 2})

# 构建 pod 资源规格，按 k8s 格式书写
SLUGBUILDER_RESOURCES_SPEC = settings.get('SLUGBUILDER_RESOURCES_SPEC')


# ---------------
# 部署环境相关
# ---------------
# 环境变量前缀
SYSTEM_CONFIG_VARS_KEY_PREFIX = settings.get('SYSTEM_CONFIG_VARS_KEY_PREFIX', 'BKPAAS_')

# 兼容内部旧的日志挂载配置
VOLUME_NAME_APP_LOGGING = settings.get('VOLUME_NAME_APP_LOGGING', 'applogs')
VOLUME_MOUNT_APP_LOGGING_DIR = settings.get('VOLUME_MOUNT_APP_LOGGING_DIR', '/app/logs')
VOLUME_HOST_PATH_APP_LOGGING_DIR = settings.get('VOLUME_HOST_PATH_APP_LOGGING_DIR', '/tmp/logs')

# 支持多模块的日志挂载配置
MUL_MODULE_VOLUME_NAME_APP_LOGGING = settings.get('MUL_MODULE_VOLUME_NAME_APP_LOGGING', 'appv3logs')
MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR = settings.get('MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR', '/app/v3logs')
MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR = settings.get(
    'MUL_MODULE_VOLUME_HOST_PATH_APP_LOGGING_DIR', '/tmp/v3logs'
)


# ---------------
# 调度集群相关
# ---------------

K8S_DEFAULT_CONNECT_TIMEOUT = 5
K8S_DEFAULT_READ_TIMEOUT = 60

# 指定 kubectl 使用的 config.yaml 文件路径，容器化交付时由 secret 挂载而来
KUBE_CONFIG_FILE = settings.get('KUBE_CONFIG_FILE', '/data/kubelet/conf/kubeconfig.yaml')

# 和 Deployment 资源回滚相关，设置值宜小，减轻 controller-manager 压力
MAX_RS_RETAIN = 3

# SLUG 最长存活时间
MAX_SLUG_SECONDS = 15 * 60

# 部署资源规则映射版本
GLOBAL_DEFAULT_MAPPER_VERSION = "v1"
LEGACY_MAPPER_VERSION = "v1"

# 默认读取 POD 最近日志行数
DEFAULT_POD_LOGS_LINE = 512


# ---------------
# Ingress 配置
# ---------------

# 不指定则使用默认，可以指定为 bk-ingress-nginx
APP_INGRESS_CLASS = settings.get('APP_INGRESS_CLASS')

# ingress extensions/v1beta1 资源路径是否保留末尾斜杠
APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH = settings.get('APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH', True)

# 是否开启“现代” Ingress 资源的支持，将产生以下影响
# - 支持使用 networking.k8s.io/v1 版本的 Ingress 资源
# - （**重要**）对于 K8S >= 1.22 版本的集群, 必须开启该选项。因为这些集群只能使用 networking.k8s.io/v1 版本的 Ingress 资源
# - （**重要**）对于 K8S >= 1.22 版本的集群, 必须使用 >1.0.0 版本的 ingress-nginx
#
# 假如关闭此配置，可能有以下风险：
#  - 只能处理 extensions/v1beta1 和 networking.k8s.io/v1beta1 版本的 Ingress 资源, 如果未来的 Kubernetes 集群版本删除了对该
#    apiVersion 的支持，服务会报错
#  - 只能使用 <1.0 版本的 ingress-nginx
ENABLE_MODERN_INGRESS_SUPPORT = settings.get('ENABLE_MODERN_INGRESS_SUPPORT', True)

# 是否开启终端色彩
COLORFUL_TERMINAL_OUTPUT = True

# 应用独立域名相关配置
CUSTOM_DOMAIN_CONFIG = settings.get(
    'CUSTOM_DOMAIN_CONFIG',
    {
        "enabled": True,
        # 允许用户配置的独立域名后缀列表，如果为空列表，允许任意独立域名
        "valid_domain_suffixes": settings.get('VALID_CUSTOM_DOMAIN_SUFFIXES', []),
        # 是否允许用户修改独立域名相关配置，如果为 False，只能由管理员通过后台管理界面调整应用独立域名配置
        "allow_user_modifications": True,
    },
)
