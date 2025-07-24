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

from paas_wl.infras.cluster.constants import HelmChartDeployStatus

# 目前 bk-ingress-nginx，bcs-general-pod-autoscaler 没有默认的 Quota，通过平台下发时需默认带上
CLUSTER_COMPONENT_DEFAULT_QUOTA = {
    "requests": {"cpu": "250m", "memory": "512Mi"},
    "limits": {"cpu": "4", "memory": "4Gi"},
}


class ClusterSource(StrStructuredEnum):
    """集群来源"""

    BCS = EnumField("bcs", "BCS 集群")
    NATIVE_K8S = EnumField("native_k8s", "原生 K8S 集群")


class ClusterAuthType(StrStructuredEnum):
    """集群认证类型"""

    TOKEN = EnumField("token", "Token")
    CERT = EnumField("cert", "证书")


class ClusterAPIAddressType(StrStructuredEnum):
    """集群 API 地址类型"""

    # 格式如：https://bcs-api.bk.tencent.com/clusters/BCS-K8S-00000/
    BCS_GATEWAY = EnumField("bcs_gateway", "BCS 网关")
    # 自定义地址：如：https://127.0.0.1:60035，https://kubernetes.default.svc.cluster.local 等
    CUSTOM = EnumField("custom", "自定义（如 IP / SvcName）")


class TolerationOperator(StrStructuredEnum):
    """容忍度运算符"""

    EQUAL = EnumField("Equal", "Equal")
    EXISTS = EnumField("Exists", "Exists")


class TolerationEffect(StrStructuredEnum):
    """容忍度效果"""

    NO_EXECUTE = EnumField("NoExecute", "不执行")
    NO_SCHEDULE = EnumField("NoSchedule", "不调度")
    PREFER_NO_SCHEDULE = EnumField("PreferNoSchedule", "倾向不调度")


class ClusterComponentStatus(StrStructuredEnum):
    """集群组件状态"""

    NOT_INSTALLED = EnumField("not_installed", "未安装")
    INSTALLING = EnumField("installing", "安装中")
    INSTALLED = EnumField("installed", "已安装")
    INSTALLATION_FAILED = EnumField("installation_failed", "安装失败")

    @classmethod
    def from_helm_release_status(cls, status: HelmChartDeployStatus) -> "ClusterComponentStatus":
        if status == HelmChartDeployStatus.DEPLOYED:
            return cls.INSTALLED

        if status == HelmChartDeployStatus.FAILED:
            return cls.INSTALLATION_FAILED

        if status in [
            HelmChartDeployStatus.PENDING_INSTALL,
            HelmChartDeployStatus.PENDING_UPGRADE,
            HelmChartDeployStatus.PENDING_ROLLBACK,
        ]:
            return cls.INSTALLING

        return cls.NOT_INSTALLED
