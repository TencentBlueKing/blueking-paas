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

from rest_framework import serializers

from paas_wl.infras.cluster.constants import HelmChartDeployStatus
from paasng.plat_mgt.infras.clusters.constants import ClusterComponentStatus


class ClusterComponentListOutputSLZ(serializers.Serializer):
    """集群组件列表"""

    name = serializers.CharField(help_text="组件名称")
    required = serializers.BooleanField(help_text="是否为必要组件")
    status = serializers.ChoiceField(help_text="组件状态", choices=ClusterComponentStatus.get_choices())


class HelmChartSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="Chart 名称")
    version = serializers.CharField(help_text="Chart 版本")
    app_version = serializers.CharField(help_text="应用版本")
    description = serializers.CharField(help_text="Chart 描述")


class HelmReleaseSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="Release 名称")
    namespace = serializers.CharField(help_text="部署的命名空间")
    version = serializers.CharField(help_text="Release 版本")
    deployed_at = serializers.DateTimeField(help_text="部署时间")
    description = serializers.CharField(help_text="部署描述")
    status = serializers.ChoiceField(help_text="部署状态", choices=HelmChartDeployStatus.get_choices())


class WorkloadSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="名称")
    kind = serializers.CharField(help_text="资源类型")
    summary = serializers.CharField(help_text="状态小结")
    conditions = serializers.JSONField(help_text="详情")


class ClusterComponentRetrieveOutputSLZ(serializers.Serializer):
    """集群组件详情"""

    chart = HelmChartSLZ(help_text="Helm Chart 信息")
    release = HelmReleaseSLZ(help_text="Helm Release 信息")
    values = serializers.JSONField(help_text="组件配置（特殊指定部分，非全量）")
    status = serializers.ChoiceField(help_text="组件状态", choices=ClusterComponentStatus.get_choices())
    workloads = serializers.ListField(help_text="工作负载列表", child=WorkloadSLZ())


class ClusterComponentUpsertInputSLZ(serializers.Serializer):
    """创建/更新集群组件"""

    values = serializers.JSONField(help_text="组件安装配置")


class ClusterComponentDiffVersionOutputSLZ(serializers.Serializer):
    """集群组件版本对比"""

    current_version = serializers.CharField(help_text="当前版本", allow_null=True)
    latest_version = serializers.CharField(help_text="最新版本", allow_null=True)
