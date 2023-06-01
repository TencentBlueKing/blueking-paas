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
from typing import Dict

from blue_krill.data_types.enum import EnumField, FeatureFlag, FeatureFlagField, StructuredEnum
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.platform.log.constants import LogCollectorType


class ClusterTokenType(int, StructuredEnum):
    SERVICE_ACCOUNT = 1


class ClusterType(str, StructuredEnum):
    """集群类别"""

    NORMAL = EnumField('normal', label=_('普通集群'))
    VIRTUAL = EnumField('virtual', label=_('虚拟集群'))


class ClusterFeatureFlag(FeatureFlag):  # type: ignore
    """集群特性标志"""

    ENABLE_EGRESS_IP = FeatureFlagField(label=_('支持提供出口 IP'), default=False)
    ENABLE_MOUNT_LOG_TO_HOST = FeatureFlagField(label=_('允许挂载日志到主机'), default=True)
    # Indicates if the paths defined on an Ingress use regular expressions
    # if not use regex, the cluster can only deploy ingress-nginx-controller <= 0.21.0
    # Because in ingress-nginx-controller >= 0.22.0, any substrings within the request URI that
    # need to be passed to the rewritten path must explicitly be defined in a capture group.
    # Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
    INGRESS_USE_REGEX = FeatureFlagField(label=_("Ingress路径是否使用正则表达式"), default=False)
    # 低于 k8s 1.12 的集群不支持蓝鲸监控
    ENABLE_BK_MONITOR = FeatureFlagField(label=_("支持蓝鲸监控"), default=False)
    # 低于 k8s 1.12 的集群不支持蓝鲸日志平台采集器
    ENABLE_BK_LOG_COLLECTOR = FeatureFlagField(
        # 如果 LOG_COLLECTOR_TYPE 设置成 BK_LOG(即只用蓝鲸日志采集链路)
        # 那么平台将不支持 1.12(含)以下的 k8s 集群
        label=_("使用蓝鲸日志平台方案采集日志"),
        default=settings.LOG_COLLECTOR_TYPE == LogCollectorType.BK_LOG,
    )
    # 低于 k8s 1.9 的集群无法支持 GPA
    ENABLE_AUTOSCALING = FeatureFlagField(label=_("支持自动扩容"), default=False)

    @classmethod
    def get_default_flags_by_cluster_type(cls, cluster_type: ClusterType) -> Dict[str, bool]:
        """get default flags by cluster_type

        for virtual cluster, ENABLE_MOUNT_LOG_TO_HOST is default to False"""
        default_flags = cls.get_default_flags()
        if cluster_type == ClusterType.VIRTUAL:
            default_flags[cls.ENABLE_MOUNT_LOG_TO_HOST] = False
        return default_flags
