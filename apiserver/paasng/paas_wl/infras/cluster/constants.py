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

from typing import Dict

from blue_krill.data_types.enum import EnumField, FeatureFlag, FeatureFlagField, IntStructuredEnum, StrStructuredEnum
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ClusterTokenType(IntStructuredEnum):
    SERVICE_ACCOUNT = 1


class ClusterType(StrStructuredEnum):
    """集群类别"""

    NORMAL = EnumField("normal", label=_("普通集群"))
    VIRTUAL = EnumField("virtual", label=_("虚拟集群"))


LOG_COLLECTOR_TYPE_BK_LOG = "BK_LOG"
BK_LOG_DEFAULT_ENABLED = settings.LOG_COLLECTOR_TYPE == LOG_COLLECTOR_TYPE_BK_LOG


class ClusterFeatureFlag(FeatureFlag):  # type: ignore
    """集群特性标志"""

    ENABLE_MOUNT_LOG_TO_HOST = FeatureFlagField(label=_("允许挂载日志到主机"), default=True)
    # Indicates if the paths defined on an Ingress use regular expressions
    # if not use regex, the cluster can only deploy ingress-nginx-controller <= 0.21.0
    # Because in ingress-nginx-controller >= 0.22.0, any substrings within the request URI that
    # need to be passed to the rewritten path must explicitly be defined in a capture group.
    # Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
    INGRESS_USE_REGEX = FeatureFlagField(label=_("Ingress路径是否使用正则表达式"), default=False)
    # 低于 k8s 1.12 的集群不支持蓝鲸监控
    ENABLE_BK_MONITOR = FeatureFlagField(label=_("从蓝鲸监控查询资源使用率"), default=False)
    # 低于 k8s 1.12 的集群不支持蓝鲸日志平台采集器
    ENABLE_BK_LOG_COLLECTOR = FeatureFlagField(
        # 如果 LOG_COLLECTOR_TYPE 设置成 BK_LOG(即只用蓝鲸日志采集链路)
        # 那么平台将不支持 1.12(含)以下的 k8s 集群
        label=_("使用蓝鲸日志平台方案采集日志"),
        default=BK_LOG_DEFAULT_ENABLED,
    )
    # 低于 k8s 1.9 的集群无法支持 GPA
    ENABLE_AUTOSCALING = FeatureFlagField(label=_("支持自动扩容"), default=False)
    # 支持通过 BCS Egress Operator 提供固定的出口 IP，推荐仅在虚拟集群中使用
    ENABLE_BCS_EGRESS = FeatureFlagField(label=_("支持 BCS Egress"), default=False)

    @classmethod
    def get_default_flags_by_cluster_type(cls, cluster_type: ClusterType) -> Dict[str, bool]:
        """get default flags by cluster_type

        for virtual cluster, ENABLE_MOUNT_LOG_TO_HOST is default to False"""
        default_flags = cls.get_default_flags()
        if cluster_type == ClusterType.VIRTUAL:
            default_flags[cls.ENABLE_MOUNT_LOG_TO_HOST] = False
        return default_flags


class ClusterAnnotationKey(StrStructuredEnum):
    """集群注解键"""

    BCS_PROJECT_ID = EnumField("bcs_project_id", label=_("BCS 项目 ID"))
    BCS_CLUSTER_ID = EnumField("bcs_cluster_id", label=_("BCS 集群 ID"))
    BK_BIZ_ID = EnumField("bk_biz_id", label=_("蓝鲸业务 ID"))


class ClusterAllocationPolicyType(StrStructuredEnum):
    """集群分配策略类型"""

    UNIFORM = EnumField("uniform", label=_("统一分配"))
    RULE_BASED = EnumField("rule_based", label=_("按规则分配"))


class ClusterAllocationPolicyCondType(StrStructuredEnum):
    """集群分配策略匹配条件"""

    REGION_IS = EnumField("region_is", label=_("可用区域为"))


class ClusterComponentName(StrStructuredEnum):
    """集群组件名称"""

    BK_INGRESS_NGINX = EnumField("bk-ingress-nginx")
    BKAPP_LOG_COLLECTION = EnumField("bkapp-log-collection")
    BKPAAS_APP_OPERATOR = EnumField("bkpaas-app-operator")
    BCS_GENERAL_POD_AUTOSCALER = EnumField("bcs-general-pod-autoscaler")
