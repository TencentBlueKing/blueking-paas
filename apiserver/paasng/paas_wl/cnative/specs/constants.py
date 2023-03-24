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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

DEFAULT_PROCESS_NAME = 'web'

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
# 注解中存储镜像凭证引用的键名
IMAGE_CREDENTIALS_REF_ANNO_KEY = "bkapp.paas.bk.tencent.com/image-credentials"


class ApiVersion(str, StructuredEnum):
    """Kubernetes CRD API versions"""

    V1ALPHA1 = 'paas.bk.tencent.com/v1alpha1'


class DeployStatus(str, StructuredEnum):
    """Cloud-native app's deployment statuses"""

    PENDING = EnumField('pending', label=_('待实施'))
    PROGRESSING = EnumField('progressing', label=_('进行中'))
    READY = EnumField('ready', label=_('已就绪'))
    ERROR = EnumField('error', label=_('错误'))
    UNKNOWN = EnumField('unknown', label=_('未知'))

    @classmethod
    def is_stable(cls, val: 'DeployStatus') -> bool:
        """Check if a status is stable, which means it will not transform into
        other statuses.
        """
        return val in [DeployStatus.READY, DeployStatus.ERROR]


class DomainGroupSource(str, StructuredEnum):
    """The source types for DomainGroup data"""

    SUBDOMAIN = 'subdomain'
    SUBPATH = 'subpath'
    CUSTOM = 'custom'


class MResConditionType(str, StructuredEnum):
    APP_AVAILABLE = EnumField("AppAvailable")
    APP_PROGRESSING = EnumField("AppProgressing")
    ADDONS_PROVISIONED = EnumField("AddOnsProvisioned")
    HOOKS_FINISHED = EnumField("HooksFinished")


class ConditionStatus(str, StructuredEnum):
    """k8s metav1.ConditionStatus"""

    TRUE = EnumField("True")
    FALSE = EnumField("False")
    UNKNOWN = EnumField("Unknown")


class MResPhaseType(str, StructuredEnum):
    """a label for the condition of a BkApp at the current time."""

    AppPending = EnumField("Pending")
    AppRunning = EnumField("Running")
    AppFailed = EnumField("Failed")
