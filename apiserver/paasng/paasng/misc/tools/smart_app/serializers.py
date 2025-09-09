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

from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.platform.engine.constants import JobStatus


class ToolPackageStashInputSLZ(serializers.Serializer):
    """Handle package for S-mart build"""

    package = serializers.FileField(help_text="待构建的应用源码包")


class BaseSmartBuildSLZ(serializers.Serializer):
    app_code = serializers.CharField(help_text="应用 code")
    signature = serializers.CharField(help_text="数字签名")


class ToolPackageStashOutputSLZ(BaseSmartBuildSLZ):
    """Tool Package Stash Output SLZ"""


class SmartBuildInputSLZ(BaseSmartBuildSLZ):
    """S-mart build request parameters SLZ"""


class SmartBuildOutputSLZ(serializers.Serializer):
    """S-mart build response SLZ"""

    build_id = serializers.CharField(help_text="构建 id")
    stream_url = serializers.URLField(help_text="获取构建进度的 stream url")


class SmartBuildFrameStepSLZ(serializers.Serializer):
    display_name = serializers.SerializerMethodField()
    name = serializers.CharField()

    def get_display_name(self, obj) -> str:
        return obj.display_name or obj.name


class SmartBuildFramePhaseSLZ(serializers.Serializer):
    display_name = serializers.SerializerMethodField(help_text="阶段展示名称")
    type = serializers.CharField(help_text="阶段类型")
    steps = SmartBuildFrameStepSLZ(source="_sorted_steps", many=True, help_text="步骤列表")

    def get_display_name(self, obj) -> str:
        return SmartBuildPhaseType.get_choice_label(obj.type)


class SmartBuildStepSLZ(serializers.Serializer):
    """Step 执行结果"""

    uuid = serializers.CharField()
    status = serializers.ChoiceField(choices=JobStatus.get_choices(), required=False)
    start_time = serializers.DateTimeField(required=False)
    complete_time = serializers.DateTimeField(required=False)


class SmartBuildPhaseSLZ(serializers.Serializer):
    """Phase 执行结果"""

    uuid = serializers.CharField()
    status = serializers.ChoiceField(choices=JobStatus.get_choices(), required=False)
    start_time = serializers.DateTimeField(required=False)
    complete_time = serializers.DateTimeField(required=False)
    steps = SmartBuildStepSLZ(source="_sorted_steps", many=True)
