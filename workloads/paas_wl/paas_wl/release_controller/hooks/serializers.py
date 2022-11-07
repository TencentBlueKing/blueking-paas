# -*- coding: utf-8 -*-
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
