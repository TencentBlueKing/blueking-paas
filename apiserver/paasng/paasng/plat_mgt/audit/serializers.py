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

from paasng.misc.audit.constants import AccessType, ResultCode


class BaseOperationAuditSLZ(serializers.Serializer):
    """基础操作审计序列化器"""

    target = serializers.CharField(help_text="操作对象")
    operation = serializers.CharField(help_text="操作类型")
    status = serializers.ChoiceField(source="result_code", choices=ResultCode.get_choices(), help_text="状态")
    operator = serializers.CharField(source="user.username", help_text="操作人")
    operated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created", help_text="操作时间")


class ApplicationOperationAuditOutputSLZ(BaseOperationAuditSLZ):
    """应用操作审计序列化器"""

    uuid = serializers.UUIDField(help_text="审计记录的唯一标识符")
    app_code = serializers.CharField(help_text="应用 ID")
    module_name = serializers.CharField(allow_blank=True, allow_null=True, help_text="模块名称")
    environment = serializers.CharField(allow_blank=True, allow_null=True, help_text="环境名称")


class ApplicationOperationAuditRetrieveOutputSLZ(BaseOperationAuditSLZ):
    """应用操作审计详情序列化器"""

    app_code = serializers.CharField(help_text="应用 ID")
    module_name = serializers.CharField(allow_blank=True, allow_null=True, help_text="模块名称")
    environment = serializers.CharField(allow_blank=True, allow_null=True, help_text="环境名称")
    access_type = serializers.ChoiceField(choices=AccessType.get_choices(), help_text="访问方式")
    data_before = serializers.JSONField(allow_null=True, help_text="操作前的数据")
    data_after = serializers.JSONField(allow_null=True, help_text="操作后的数据")


class PlatformOperationAuditOutputSLZ(BaseOperationAuditSLZ):
    """平台操作审计序列化器"""

    uuid = serializers.UUIDField(help_text="审计记录的唯一标识符")
    attribute = serializers.CharField(allow_blank=True, allow_null=True, help_text="操作属性")


class PlatformOperationAuditRetrieveOutputSLZ(BaseOperationAuditSLZ):
    """平台操作审计详情序列化器"""

    attribute = serializers.CharField(allow_blank=True, allow_null=True, help_text="操作属性")
    access_type = serializers.ChoiceField(choices=AccessType.get_choices(), help_text="访问方式")
    data_before = serializers.JSONField(allow_null=True, help_text="操作前的数据")
    data_after = serializers.JSONField(allow_null=True, help_text="操作后的数据")


class OperationAuditFilterInputSLZ(serializers.Serializer):
    """审计记录过滤器序列化器"""

    target = serializers.CharField(help_text="操作对象", required=False)
    operation = serializers.CharField(help_text="操作类型", required=False)
    status = serializers.ChoiceField(choices=ResultCode.get_choices(), help_text="状态", required=False)
    operator = serializers.CharField(help_text="操作人", required=False)
    start_time = serializers.DateTimeField(
        help_text="开始时间", format="%Y-%m-%d %H:%M:%S", required=False, allow_null=True
    )
    end_time = serializers.DateTimeField(
        help_text="结束时间", format="%Y-%m-%d %H:%M:%S", required=False, allow_null=True
    )
