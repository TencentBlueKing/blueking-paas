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
from builtins import object

from rest_framework import serializers

from paasng.platform.applications.models import Application
from paasng.platform.applications.serializers import ApplicationMinimalSLZ, ApplicationSLZ4Record
from paasng.platform.operations.models import Operation


class OperationSLZ(serializers.ModelSerializer):
    application = ApplicationSLZ4Record(read_only=True)
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created")
    operator = serializers.ReadOnlyField(source="get_operator", read_only=True)
    operate = serializers.ReadOnlyField(source="get_operate_display", help_text=u"操作名称")
    operate_type = serializers.ReadOnlyField(source="type", help_text=u"操作类型")

    class Meta(object):
        model = Operation
        fields = ("application", "id", "region", "at", "operate", "operate_type", "operator")
        lookup_field = "id"


class OperationForRencentApp(OperationSLZ):
    application = ApplicationSLZ4Record(read_only=True)
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created")
    operate = serializers.ReadOnlyField(source="get_operate_display", help_text=u"操作名称")
    operate_type = serializers.ReadOnlyField(source="type", help_text=u"操作类型")
    represent_info = serializers.DictField()

    class Meta(object):
        model = Operation
        fields = ("application", "id", "at", "operate", "operate_type", 'represent_info')
        lookup_field = "id"


class RecentOperationsByAppSLZ(serializers.Serializer):
    results = OperationForRencentApp(many=True)


class ApplicationOperationSLZ(serializers.ModelSerializer):
    application = ApplicationMinimalSLZ(read_only=True)
    module_name = serializers.CharField(help_text="关联 Module")
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created")
    operator = serializers.ReadOnlyField(source="get_operator", read_only=True)
    operate = serializers.ReadOnlyField(source="get_operate_display", help_text=u"操作名称")
    operate_type = serializers.ReadOnlyField(source="type", help_text=u"操作类型")

    class Meta(object):
        model = Operation
        fields = (
            "application",
            "id",
            "region",
            "at",
            "operate",
            "operate_type",
            "operator",
            "extra_values",
            "module_name",
        )
        lookup_field = "id"


class QueryRecentOperatedApplications(serializers.Serializer):
    limit = serializers.IntegerField(default=4, max_value=10, help_text='条目数')


class SysOperationSLZ(serializers.Serializer):
    """Serializer for `Operation` model, on "system-api" level"""

    application = serializers.PrimaryKeyRelatedField(queryset=Application.objects.all())
    operator = serializers.CharField(help_text='操作者ID', required=True)
    operate_type = serializers.IntegerField(help_text="操作类型", required=True)

    # Optional fields
    module_name = serializers.CharField(help_text='模块名', required=False)
    source_object_id = serializers.CharField(help_text='被操作对象ID', required=False)
    extra_values = serializers.JSONField(help_text=u"附加数据", required=False)
