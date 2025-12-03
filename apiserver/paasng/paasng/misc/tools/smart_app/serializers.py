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

from typing import List

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.engine.constants import JobStatus
from paasng.utils.i18n.serializers import TranslatedCharField
from paasng.utils.models import OrderByField
from paasng.utils.serializers import StringArrayField

from .constants import SourceCodeOriginType


class ToolPackageStashInputSLZ(serializers.Serializer):
    """Upload source package SLZ"""

    package = serializers.FileField(help_text="待构建的应用源码包")


class BaseSmartBuildSLZ(serializers.Serializer):
    """Base SLZ for Smart Build APIs"""

    app_code = serializers.CharField(help_text="应用 code")
    signature = serializers.CharField(help_text="数字签名")


class ToolPackageStashOutputSLZ(BaseSmartBuildSLZ):
    """Upload source package response SLZ"""


class SmartBuildInputSLZ(BaseSmartBuildSLZ):
    """Input SLZ for Smart Build API"""


class SmartBuildOutputSLZ(serializers.Serializer):
    """Output SLZ for Smart Build API"""

    build_id = serializers.CharField(help_text="构建 ID")
    stream_url = serializers.URLField(help_text="构建进度 Stream URL")


class SmartBuildFrameStepSLZ(serializers.Serializer):
    """Step SLZ for Smart Build Frame"""

    display_name = TranslatedCharField()
    name = serializers.CharField()


class SmartBuildRecordFilterInputSLZ(serializers.Serializer):
    """SmartBuild record filter SLZ"""

    source_origin = serializers.ChoiceField(
        required=False, choices=SourceCodeOriginType.get_choices(), help_text="源码来源"
    )
    search = serializers.CharField(required=False, help_text="关键字搜索")
    status = serializers.ChoiceField(required=False, choices=JobStatus.get_choices(), help_text="构建状态")
    order_by = StringArrayField(required=False, default=["-created"], help_text="排序字段")

    def validate_order_by(self, fields: List[str]) -> List[str]:
        """校验排序字段"""
        valid_order_by_fields = ["created"]
        for field in fields:
            f = OrderByField.from_string(field)
            if f.name not in valid_order_by_fields:
                raise ValidationError(f"Invalid order_by field: {field}")
        return fields


class SmartBuildHistoryOutputSLZ(serializers.Serializer):
    """SmartBuild history output SLZ"""

    uuid = serializers.CharField(help_text="构建 ID")
    app_code = serializers.CharField(help_text="应用 code")
    app_version = serializers.CharField(help_text="应用版本号")
    source_origin = serializers.CharField(help_text="源码来源")
    package_name = serializers.CharField(help_text="源码包名")
    sha256_signature = serializers.CharField(help_text="源码包 sha256 签名")
    status = serializers.CharField(help_text="构建状态")
    start_time = serializers.DateTimeField(help_text="开始时间", allow_null=True)
    end_time = serializers.DateTimeField(help_text="结束时间", allow_null=True)
    created = serializers.DateTimeField(help_text="创建时间")


class SmartBuildHistoryLogsOutputSLZ(serializers.Serializer):
    """SmartBuild history logs output SLZ"""

    status = serializers.ChoiceField(JobStatus.get_choices(), help_text="构建状态")
    start_time = serializers.DateTimeField(help_text="开始时间", allow_null=True)
    end_time = serializers.DateTimeField(help_text="结束时间", allow_null=True)
    logs = serializers.CharField(help_text="构建日志")
