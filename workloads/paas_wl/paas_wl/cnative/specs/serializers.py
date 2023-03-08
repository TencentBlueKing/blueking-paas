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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .constants import DeployStatus
from .models import AppModelDeploy


class AppModelResourceSerializer(serializers.Serializer):
    """云原生架构应用 Serializer"""

    application_id = serializers.UUIDField(label=_('所属应用'))
    module_id = serializers.UUIDField(label=_('所属模块'))
    manifest = serializers.JSONField(label=_('BkApp 配置信息'), source='revision.json_value')


class CreateDeploySerializer(serializers.Serializer):
    """部署云原生应用 Serializer"""

    # TODO: 后续支持版本与部署分离，可以通过指定版本号的方式部署
    # 不提供时，使用应用当前 revision 所指向的 manifest 值
    manifest = serializers.JSONField(label=_('BkApp 配置信息'), required=False)


class ProcReplicasChangeSLZ(serializers.Serializer):
    """Format `ProcReplicasChange` object"""

    proc_type = serializers.CharField(label=_('进程类型'))
    old = serializers.IntegerField(label=_('旧副本数'))
    new = serializers.IntegerField(label=_('新副本数'))


class DeployPrepResultSLZ(serializers.Serializer):
    """Format deploy preparation result"""

    proc_replicas_changes = serializers.ListField(label=_('进程副本数变化'), child=ProcReplicasChangeSLZ())


class QueryDeploysSerializer(serializers.Serializer):
    """Serializer for querying AppModelDeploy objects"""

    operator = serializers.CharField(label=_('操作者'), required=False)


class DeployDetailSerializer(serializers.ModelSerializer):
    """Serializer for representing detailed AppModelDeploy object"""

    manifest = serializers.JSONField(label=_('BkApp 配置信息'), source='revision.json_value')
    operator = serializers.CharField(source='operator.username')

    class Meta:
        model = AppModelDeploy
        exclude = ('module_id',)


class DeploySerializer(serializers.ModelSerializer):
    """Serializer for representing AppModelDeploy objects"""

    operator = serializers.CharField(source='operator.username')

    class Meta:
        model = AppModelDeploy
        exclude = ('module_id',)


class MresDeploymentStatusSLZ(serializers.Serializer):
    """Serializer for ModelResource deployment status"""

    deploy_id = serializers.IntegerField(help_text="部署ID", source="pk")
    status = serializers.ChoiceField(choices=DeployStatus.get_choices(), default=DeployStatus.UNKNOWN)
    reason = serializers.CharField(allow_blank=True)
    message = serializers.CharField(allow_blank=True)
    last_transition_time = serializers.DateTimeField()

    operator = serializers.CharField(source='operator.username', help_text="操作人")
    created = serializers.DateTimeField(help_text="发布时间")


class MresIngressInfoSLZ(serializers.Serializer):
    """Serializer for ModelResource Ingress info"""

    url = serializers.CharField(allow_null=True, allow_blank=True)


class MresConditionSLZ(serializers.Serializer):
    """Serializer for ModelResource Condition Field"""

    type = serializers.CharField()
    status = serializers.ChoiceField(choices=DeployStatus.get_choices(), default=DeployStatus.UNKNOWN)
    reason = serializers.CharField(allow_blank=True)
    message = serializers.CharField(allow_blank=True)


class KubeEventSLZ(serializers.Serializer):
    """Serializer for k8s event"""

    name = serializers.CharField(help_text="事件名称")
    type = serializers.CharField(help_text="事件级别")
    reason = serializers.CharField(help_text="事件原因")
    count = serializers.CharField(help_text="事件累计触发次数")
    message = serializers.CharField(help_text="事件消息内容")
    source_component = serializers.CharField(help_text="事件来源组件")
    first_seen = serializers.DateTimeField(help_text="事件首次被记录的时间")
    last_seen = serializers.DateTimeField(help_text="事件最后被记录的时间")


class MresStatusSLZ(serializers.Serializer):
    """Serializer for ModelResource status"""

    deployment = MresDeploymentStatusSLZ()
    ingress = MresIngressInfoSLZ()
    conditions = MresConditionSLZ(many=True)
    events = KubeEventSLZ(many=True)
