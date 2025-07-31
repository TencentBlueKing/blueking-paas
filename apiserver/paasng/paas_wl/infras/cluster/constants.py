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
    INGRESS_USE_REGEX = FeatureFlagField(label=_("Ingress 路径是否使用正则表达式"), default=False)
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
    # 集群配置了子域名, 并且子域名有证书，才能启用 gRPC Ingress
    ENABLE_GRPC_INGRESS = FeatureFlagField(label=_("支持 gRPC Ingress"), default=False)


class ClusterAnnotationKey(StrStructuredEnum):
    """集群注解键"""

    BCS_PROJECT_ID = EnumField("bcs_project_id", label=_("BCS 项目 ID"))
    BCS_CLUSTER_ID = EnumField("bcs_cluster_id", label=_("BCS 集群 ID"))
    BK_BIZ_ID = EnumField("bk_biz_id", label=_("蓝鲸业务 ID"))
    SKIP_INJECT_BUILTIN_IMAGE_CREDENTIAL = EnumField(
        "skip_inject_builtin_image_credential", label=_("跳过内置镜像凭证注入")
    )
    # NOTE: 该配置仅对普通应用生效，云原生应用需要在 Operator 的 Helm Chart Values 中配置
    INGRESS_CLASS_NAME = EnumField("ingress_class_name", label=_("Ingress 类名"))
    # 集群 slugbuilder 资源配额，其值格式如下（非字符串）：
    # {"requests": {"cpu": "1", "memory": "1Gi"}, "limits": {"cpu": "4", "memory": "4Gi"}}
    SLUGBUILDER_RESOURCE_QUOTA = EnumField("slugbuilder_resource_quota", label=_("Slugbuilder 资源配额"))


class ClusterAllocationPolicyType(StrStructuredEnum):
    """集群分配策略类型"""

    UNIFORM = EnumField("uniform", label=_("统一分配"))
    RULE_BASED = EnumField("rule_based", label=_("按规则分配"))


class ClusterAllocationPolicyCondType(StrStructuredEnum):
    """集群分配策略匹配条件"""

    REGION_IS = EnumField("region_is", label="Region")
    USERNAME_IN = EnumField("username_in", label="Username.In")


class ClusterComponentName(StrStructuredEnum):
    """集群组件名称"""

    BK_INGRESS_NGINX = EnumField("bk-ingress-nginx")
    BKPAAS_APP_OPERATOR = EnumField("bkpaas-app-operator")
    BKAPP_LOG_COLLECTION = EnumField("bkapp-log-collection")
    BK_LOG_COLLECTOR = EnumField("bk-log-collector")
    BCS_GENERAL_POD_AUTOSCALER = EnumField("bcs-general-pod-autoscaler")


class HelmChartDeployStatus(StrStructuredEnum):
    """
    Helm Chart 部署状态

    ref: https://github.com/helm/helm/blob/fb54996b001697513cdb1ffa5915c0ba90149fff/pkg/release/status.go#L19
    """

    UNKNOWN = EnumField("unknown", "未知")
    FAILED = EnumField("failed", "失败")
    DEPLOYED = EnumField("deployed", "部署完成")
    SUPERSEDED = EnumField("superseded", "被取代")
    UNINSTALLING = EnumField("uninstalling", "卸载中")
    UNINSTALLED = EnumField("uninstalled", "已卸载")

    PENDING_INSTALL = EnumField("pending-install", "待安装")
    PENDING_UPGRADE = EnumField("pending-upgrade", "待升级")
    PENDING_ROLLBACK = EnumField("pending-rollback", "待回滚")
