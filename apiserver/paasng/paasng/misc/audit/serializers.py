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

from paasng.misc.audit.models import AppOperationRecord
from paasng.platform.applications.serializers import ApplicationSLZ4Record


class AppOperationRecordSLZ(serializers.ModelSerializer):
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created")
    operate = serializers.ReadOnlyField(source="get_display_text", help_text="操作名称")
    operator = serializers.ReadOnlyField(source="username", read_only=True)

    class Meta:
        model = AppOperationRecord
        fields = "__all__"


class QueryRecentOperationsSLZ(serializers.Serializer):
    limit = serializers.IntegerField(default=4, max_value=10, help_text="条目数")


class RecordForRencentAppSLZ(AppOperationRecordSLZ):
    application = ApplicationSLZ4Record(read_only=True)

    class Meta:
        model = AppOperationRecord
        fields = "__all__"
