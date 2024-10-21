# -*- coding: utf-8 -*-
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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.utils.translation import gettext_lazy as _

# Default resource limitations for each process
DEFAULT_PROC_CPU = "4000m"
DEFAULT_PROC_MEM = "1024Mi"
# Default resource request for each process
DEFAULT_PROC_CPU_REQUEST = "200m"
DEFAULT_PROC_MEM_REQUEST = "256Mi"

DEFAULT_PROCESS_NAME = "web"

# 注解中存储当前应用是否启用白名单功能的键名
ACCESS_CONTROL_ANNO_KEY = "bkapp.paas.bk.tencent.com/access-control"
# workloads 注入到 annotations 的部署ID字段
BKPAAS_DEPLOY_ID_ANNO_KEY = "bkapp.paas.bk.tencent.com/bkpaas-deploy-id"
# workloads 注入到 annotations 的增强服务信息字段
BKPAAS_ADDONS_ANNO_KEY = "bkapp.paas.bk.tencent.com/addons"
# 注解中存储 region 的键名
BKAPP_REGION_ANNO_KEY = "bkapp.paas.bk.tencent.com/region"
# 注解或标签中存储应用名称的键名
BKAPP_NAME_ANNO_KEY = "bkapp.paas.bk.tencent.com/name"
# 注解中存储应用 ID 的键名
BKAPP_CODE_ANNO_KEY = "bkapp.paas.bk.tencent.com/code"
# 注解中存储模块名称的键名
MODULE_NAME_ANNO_KEY = "bkapp.paas.bk.tencent.com/module-name"
# 注解中存储当前部署环境的键名
ENVIRONMENT_ANNO_KEY = "bkapp.paas.bk.tencent.com/environment"
# 注解中存储当前 WlApp 名称的键名
WLAPP_NAME_ANNO_KEY = "bkapp.paas.bk.tencent.com/wl-app-name"
# 注解中存储镜像凭证引用的键名
IMAGE_CREDENTIALS_REF_ANNO_KEY = "bkapp.paas.bk.tencent.com/image-credentials"
# 注解中存储数据统计站点ID的键名
PA_SITE_ID_ANNO_KEY = "bkapp.paas.bk.tencent.com/paas-analysis-site-id"
# 注解中存储资源类型的键名
RESOURCE_TYPE_KEY = "bkapp.paas.bk.tencent.com/resource-type"
# 注解中声明镜像类型是否 cnb 的键名
USE_CNB_ANNO_KEY = "bkapp.paas.bk.tencent.com/use-cnb"
# 注解中存储日志采集类型相关的键名
LOG_COLLECTOR_TYPE_ANNO_KEY = "bkapp.paas.bk.tencent.com/log-collector-type"

# 轮询云原生应用的部署状态时，如果获取到失败状态的次数超过最大容忍次数，就认为部署失败
CNATIVE_DEPLOY_STATUS_POLLING_FAILURE_LIMITS = 3

# PROC_SERVICES_ENABLED_ANNOTATION_KEY 注解表示是否启用 process services 特性, 可选值为 "true" 或 "false".
# true 表示 operator 将根据 process services 的配置来创建和关联 k8s service.
# 该注解实际为了向后兼容 spec_version: 2 而设计, 当版本 <= spec_version: 2 时, 设置值为 "false", 否则设置为 "true".
# 说明: 未设置该注解值的 BkApp 均是线上存量资源, 为了兼容, operator 会继续按照旧逻辑调和.
PROC_SERVICES_ENABLED_ANNOTATION_KEY = "bkapp.paas.bk.tencent.com/proc-services-feature-enabled"


class ApiVersion(StrStructuredEnum):
    """Kubernetes CRD API versions"""

    V1ALPHA1 = "paas.bk.tencent.com/v1alpha1"
    V1ALPHA2 = "paas.bk.tencent.com/v1alpha2"


class DeployStatus(StrStructuredEnum):
    """Cloud-native app's deployment statuses"""

    PENDING = EnumField("pending", label=_("待实施"))
    PROGRESSING = EnumField("progressing", label=_("进行中"))
    READY = EnumField("ready", label=_("已就绪"))
    ERROR = EnumField("error", label=_("错误"))
    UNKNOWN = EnumField("unknown", label=_("未知"))

    @classmethod
    def is_stable(cls, val: "DeployStatus") -> bool:
        """Check if a status is stable, which means it will not transform into
        other statuses.
        """
        return val in [DeployStatus.READY, DeployStatus.ERROR]


class DomainGroupSource(StrStructuredEnum):
    """The source types for DomainGroup data"""

    SUBDOMAIN = "subdomain"
    SUBPATH = "subpath"
    CUSTOM = "custom"


class MResConditionType(StrStructuredEnum):
    APP_AVAILABLE = EnumField("AppAvailable")
    APP_PROGRESSING = EnumField("AppProgressing")
    ADDONS_PROVISIONED = EnumField("AddOnsProvisioned")
    HOOKS_FINISHED = EnumField("HooksFinished")


class ConditionStatus(StrStructuredEnum):
    """k8s metav1.ConditionStatus"""

    TRUE = EnumField("True")
    FALSE = EnumField("False")
    UNKNOWN = EnumField("Unknown")


class MResPhaseType(StrStructuredEnum):
    """a label for the condition of a BkApp at the current time."""

    AppPending = EnumField("Pending")
    AppRunning = EnumField("Running")
    AppFailed = EnumField("Failed")


class ScalingPolicy(StrStructuredEnum):
    """ScalingPolicy is used to specify which policy should be used while scaling"""

    # the default autoscaling policy (cpu utilization 85%)
    DEFAULT = EnumField("default")


class ResQuotaPlan(StrStructuredEnum):
    """ResQuotaPlan is used to specify process resource quota"""

    P_DEFAULT = EnumField("default", label="default")
    P_4C1G = EnumField("4C1G", label="4C1G")
    P_4C2G = EnumField("4C2G", label="4C2G")
    P_4C4G = EnumField("4C4G", label="4C4G")


class MountEnvName(StrStructuredEnum):
    """Environment name for managing mount volume"""

    STAG = EnumField("stag", label="仅测试环境")
    PROD = EnumField("prod", label="仅生产环境")
    GLOBAL = EnumField("_global_", label="所有环境")


class VolumeSourceType(StrStructuredEnum):
    ConfigMap = EnumField("ConfigMap")
    PersistentStorage = EnumField("PersistentStorage")


class PersistentStorageSize(StrStructuredEnum):
    P_1G = EnumField("1Gi")
    P_2G = EnumField("2Gi")
    P_4G = EnumField("4Gi")
