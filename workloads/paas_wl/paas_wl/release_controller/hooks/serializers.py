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
from rest_framework import serializers

from paas_wl.platform.system_api.serializers import LineSerializer
from paas_wl.utils.constants import CommandStatus, CommandType

################
#   Command    #
################


class CreateCommandSerializer(serializers.Serializer):
    """Serializer for Creating Command"""

    type = serializers.ChoiceField(choices=CommandType.get_choices())
    command = serializers.CharField(required=True)
    build = serializers.CharField(required=True)
    operator = serializers.CharField(required=True, help_text="操作者(被编码的 username)")
    stream_channel_id = serializers.CharField(required=False, min_length=32)

    extra_envs = serializers.JSONField(required=False, help_text="额外的环境变量", default=dict, allow_null=True)


class SimpleCommandSerializer(serializers.Serializer):
    """Serializer for Command"""

    uuid = serializers.UUIDField()
    command = serializers.CharField(required=True)
    operator = serializers.CharField(required=True, help_text="操作者(被编码的 username)")
    version = serializers.IntegerField()
    stream_channel_id = serializers.CharField(required=False, min_length=32)

    status = serializers.ChoiceField(choices=CommandStatus.get_choices())
    exit_code = serializers.IntegerField(allow_null=True)

    def to_representation(self, instance):
        # 暂时由 engine 屏蔽掉 SCHEDULED 这个状态.
        data = super().to_representation(instance)
        if data["status"] == CommandStatus.SCHEDULED.value:
            data["status"] = CommandStatus.PENDING.value
        return data


class CommandWithLogsSerializer(SimpleCommandSerializer):
    lines = LineSerializer(many=True)
