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
from paasng.platform.engine.constants import AppEnvName


class AuditOperationListOutputSLZ(serializers.Serializer):
    uuid = serializers.UUIDField()
    operation = serializers.CharField()
    target = serializers.CharField()
    attribute = serializers.CharField(allow_blank=True, allow_null=True)
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created")
    result_code = serializers.ChoiceField(choices=ResultCode.get_choices())
    operator = serializers.CharField(source="username")


class AuditOperationRetrieveOutputSLZ(serializers.Serializer):
    operation = serializers.CharField()
    target = serializers.CharField()
    attribute = serializers.CharField(allow_blank=True, allow_null=True)
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created")
    result_code = serializers.ChoiceField(choices=ResultCode.get_choices())
    operator = serializers.CharField(source="username")
    access_type = serializers.ChoiceField(choices=AccessType.get_choices())
    data_before = serializers.JSONField(allow_null=True)
    data_after = serializers.JSONField(allow_null=True)


class AppAuditOperationListInputSLZ(serializers.Serializer):
    filter_key = serializers.CharField(default=None, required=False, allow_null=True)


class AppAuditOperationListOutputSLZ(serializers.Serializer):
    uuid = serializers.UUIDField()
    operation = serializers.CharField()
    app_code = serializers.CharField()
    target = serializers.CharField()
    module_name = serializers.CharField(allow_blank=True, allow_null=True)
    environment = serializers.CharField(allow_blank=True, allow_null=True)
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created")
    result_code = serializers.ChoiceField(choices=ResultCode.get_choices())
    operator = serializers.CharField(source="username")


class AppAuditOperationRetrieveOutputSLZ(serializers.Serializer):
    operation = serializers.CharField()
    app_code = serializers.CharField()
    target = serializers.CharField()
    module_name = serializers.CharField(allow_blank=True, allow_null=True)
    environment = serializers.ChoiceField(allow_blank=True, allow_null=True, choices=AppEnvName.get_choices())
    at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="created")
    result_code = serializers.ChoiceField(choices=ResultCode.get_choices())
    operator = serializers.CharField(source="username")
    access_type = serializers.ChoiceField(choices=AccessType.get_choices())
    data_before = serializers.JSONField(allow_null=True)
    data_after = serializers.JSONField(allow_null=True)
