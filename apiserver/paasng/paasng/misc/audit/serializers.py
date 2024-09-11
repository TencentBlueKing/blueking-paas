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

from paasng.misc.audit.constants import AccessType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.models import AppOperationRecord
from paasng.platform.applications.serializers import ApplicationSLZ4Record


class AppOperationRecordSLZ(serializers.ModelSerializer):
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created", help_text="操作时间")
    operate = serializers.ReadOnlyField(source="get_display_text", help_text="操作记录的完整展示文案")
    operator = serializers.ReadOnlyField(source="username", read_only=True, help_text="操作人")
    detail_type = serializers.SerializerMethodField(help_text="操作详情中的数据类型")

    def get_detail_type(self, obj) -> str:
        """操作详情中的数据类型，用于前端按照不同的类型来展示详情"""
        if obj.data_before:
            return obj.data_before.get("type")
        if obj.data_after:
            return obj.data_after.get("type")
        return ""

    class Meta:
        model = AppOperationRecord
        fields = "__all__"


class AppOperationRecordFilterSlZ(serializers.Serializer):
    """操作审计筛选条件"""

    target = serializers.ChoiceField(choices=OperationTarget.get_choices(), help_text="操作对象", required=False)
    operation = serializers.ChoiceField(choices=OperationEnum.get_choices(), help_text="操作类型", required=False)
    access_type = serializers.ChoiceField(choices=AccessType.get_choices(), help_text="访问方式", required=False)
    result_code = serializers.ChoiceField(choices=ResultCode.get_choices(), help_text="操作结果", required=False)
    module_name = serializers.CharField(required=False, help_text="模块")
    environment = serializers.CharField(required=False, help_text="环境")
    start_time = serializers.DateTimeField(help_text="format %Y-%m-%d %H:%M:%S", allow_null=True, required=False)
    end_time = serializers.DateTimeField(help_text="format %Y-%m-%d %H:%M:%S", allow_null=True, required=False)
    operator = serializers.CharField(required=False, help_text="操作人")


class QueryRecentOperationsSLZ(serializers.Serializer):
    limit = serializers.IntegerField(default=4, max_value=10, help_text="条目数")


class RecordForRecentAppSLZ(AppOperationRecordSLZ):
    application = ApplicationSLZ4Record(read_only=True)
    module_name = serializers.SerializerMethodField()

    def get_module_name(self, obj) -> str:
        if obj.module_name:
            return obj.module_name
        if obj.application:
            return obj.application.get_default_module().name
        return ""

    class Meta:
        model = AppOperationRecord
        fields = "__all__"
