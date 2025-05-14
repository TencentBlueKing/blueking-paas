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

from paasng.bk_plugins.bk_plugins.models import BkPluginDistributor, BkPluginTag
from paasng.bk_plugins.pluginscenter import constants


class BKPluginTagSLZ(serializers.ModelSerializer):
    class Meta:
        model = BkPluginTag
        fields = "__all__"


class BkPluginDistributorSLZ(serializers.ModelSerializer):
    class Meta:
        model = BkPluginDistributor
        fields = ("id", "name", "code_name", "bk_app_code", "introduction")


class BKPluginMembersManageReqSLZ(serializers.Serializer):
    action = serializers.CharField(required=True, help_text="动作，add 添加角色，delete 取消角色")
    role = serializers.ChoiceField(choices=constants.PluginRole.get_choices(), required=True, help_text="插件角色")

    def validate_action(self, value):
        if value not in ["add", "delete"]:
            raise serializers.ValidationError("action must be either 'add' or 'delete'.")
        return value
