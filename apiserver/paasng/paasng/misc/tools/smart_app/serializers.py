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

from typing import TYPE_CHECKING, List

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.engine.constants import JobStatus
from paasng.utils.i18n.serializers import TranslatedCharField
from paasng.utils.models import OrderByField
from paasng.utils.serializers import StringArrayField

from .constants import SmartBuildPhaseType, SourceCodeOriginType

if TYPE_CHECKING:
    from paasng.misc.tools.smart_app.models import SmartBuildRecord


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

    smart_build_id = serializers.CharField(help_text="构建 ID")
    stream_url = serializers.URLField(help_text="构建进度 Stream URL")


class SmartBuildFrameStepSLZ(serializers.Serializer):
    """Step SLZ for Smart Build Frame"""

    display_name = TranslatedCharField()
    name = serializers.CharField()


class SmartBuildFramePhaseSLZ(serializers.Serializer):
    """Phase SLZ for Smart Build Frame"""

    display_name = serializers.SerializerMethodField(help_text="阶段展示名称")
    type = serializers.CharField(help_text="阶段类型")
    steps = SmartBuildFrameStepSLZ(source="_sorted_steps", many=True, help_text="步骤列表")

    def get_display_name(self, obj) -> str:
        return SmartBuildPhaseType.get_choice_label(obj["type"])


class SmartBuildStepSLZ(serializers.Serializer):
    """Step 执行结果"""

    uuid = serializers.CharField()
    name = serializers.CharField()
    status = serializers.ChoiceField(choices=JobStatus.get_choices(), required=False)
    start_time = serializers.DateTimeField(required=False)
    complete_time = serializers.DateTimeField(required=False)


class SmartBuildPhaseSLZ(serializers.Serializer):
    """Phase 执行结果"""

    uuid = serializers.CharField()
    name = serializers.CharField(source="type")
    status = serializers.ChoiceField(choices=JobStatus.get_choices(), required=False)
    start_time = serializers.DateTimeField(required=False)
    complete_time = serializers.DateTimeField(required=False)
    steps = SmartBuildStepSLZ(source="_sorted_steps", many=True)


class SmartBuildRecordFilterInputSLZ(serializers.Serializer):
    """SmartBuild record filter SLZ"""

    valid_order_by_fields = ["created"]

    source_origin = serializers.ChoiceField(
        required=False, choices=SourceCodeOriginType.get_choices(), help_text="源码来源"
    )
    search = serializers.CharField(required=False, help_text="关键字搜索")
    status = serializers.ChoiceField(required=False, choices=JobStatus.get_choices(), help_text="构建状态")
    order_by = StringArrayField(required=False, default=["-created"], help_text="排序字段")

    def validate_order_by(self, fields: List[str]) -> List[str]:
        """校验排序字段"""
        for field in fields:
            f = OrderByField.from_string(field)
            if f.name not in self.valid_order_by_fields:
                raise ValidationError(f"Invalid order_by field: {field}")
        return fields


class SmartBuildHistoryOutputSLZ(serializers.Serializer):
    """SmartBuild history output SLZ"""

    uuid = serializers.CharField(help_text="构建 ID")
    source_origin = serializers.CharField(help_text="源码来源")
    package_name = serializers.CharField(help_text="源码包名")
    status = serializers.CharField(help_text="构建状态")
    spent_time = serializers.SerializerMethodField(help_text="耗时(秒)")
    operator = serializers.CharField(help_text="操作人")
    created = serializers.DateTimeField(help_text="创建时间")
    artifact_url = serializers.CharField(help_text="产物下载地址")

    def get_spent_time(self, obj: "SmartBuildRecord") -> int:
        if not (obj.start_time and obj.end_time):
            return 0
        return int((obj.end_time - obj.start_time).total_seconds())


class SmartBuildHistoryLogsOutputSLZ(serializers.Serializer):
    """SmartBuild history logs output SLZ"""

    status = serializers.ChoiceField(JobStatus.get_choices(), help_text="构建状态")
    logs = serializers.CharField(help_text="构建日志")
