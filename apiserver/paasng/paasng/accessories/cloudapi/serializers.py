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
from rest_framework import serializers

from . import constants


class APIGWAPISLZ(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    maintainers = serializers.ListField()


class APIGWPermissionSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    expires_in = serializers.CharField()
    permission_level = serializers.ChoiceField(
        choices=constants.PermissionLevelEnum.get_django_choices(),
    )
    permission_status = serializers.ChoiceField(
        choices=constants.PermissionStatusEnum.get_django_choices(),
    )
    permission_action = serializers.ChoiceField(
        choices=constants.PermissionActionEnum.get_django_choices(),
        allow_blank=True,
    )
    doc_link = serializers.CharField()


class APIGWPermissionApplySLZ(serializers.Serializer):
    resource_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
        required=False,
    )
    reason = serializers.CharField(max_length=512, allow_blank=True, required=False, default="")
    expire_days = serializers.ChoiceField(
        choices=constants.PermissionApplyExpireDaysEnum.get_django_choices(),
    )
    grant_dimension = serializers.ChoiceField(
        choices=constants.GrantDimensionEnum.get_django_choices(),
    )
    gateway_name = serializers.CharField(help_text="网关名称，用于记录操作记录")


class APIGWPermissionRenewSLZ(serializers.Serializer):
    resource_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        required=True,
    )
    expire_days = serializers.ChoiceField(
        choices=constants.PermissionApplyExpireDaysEnum.get_django_choices(),
    )


class APIGWAllowApplyByAPISLZ(serializers.Serializer):
    allow_apply_by_api = serializers.BooleanField()
    reason = serializers.CharField()


class APIGWPermissionApplyRecordQuerySLZ(serializers.Serializer):
    applied_by = serializers.CharField(allow_blank=True, required=False)
    applied_time_start = serializers.IntegerField(allow_null=True, required=False)
    applied_time_end = serializers.IntegerField(allow_null=True, required=False)
    apply_status = serializers.ChoiceField(
        choices=constants.ApplyStatusEnum.get_django_choices(),
        allow_blank=True,
        required=False,
    )
    query = serializers.CharField(allow_blank=True, required=False)


class APIGWPermissionApplyRecordSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    bk_app_code = serializers.CharField()
    applied_by = serializers.CharField()
    applied_time = serializers.CharField()
    handled_by = serializers.CharField()
    handled_time = serializers.CharField()
    apply_status = serializers.ChoiceField(
        choices=constants.ApplyStatusEnum.get_django_choices(),
    )
    grant_dimension = serializers.ChoiceField(
        choices=constants.GrantDimensionEnum.get_django_choices(),
    )
    comment = serializers.CharField()
    reason = serializers.CharField()
    expire_days = serializers.IntegerField()
    api_name = serializers.CharField()


class APIGWResourceApplyStatusSLZ(serializers.Serializer):
    name = serializers.CharField()
    apply_status = serializers.ChoiceField(
        choices=constants.ApplyStatusEnum.get_django_choices(),
    )


class APIGWPermissionApplyRecordDetailSLZ(APIGWPermissionApplyRecordSLZ):
    resources = serializers.ListField(child=APIGWResourceApplyStatusSLZ())


class ESBSystemSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    maintainers = serializers.ListField(child=serializers.CharField())
    tag = serializers.CharField()


class ESBPermissionApplySLZ(serializers.Serializer):
    component_ids = serializers.ListField(
        child=serializers.IntegerField(),
    )
    reason = serializers.CharField(max_length=512, allow_blank=True, required=False, default="")
    expire_days = serializers.ChoiceField(
        choices=constants.PermissionApplyExpireDaysEnum.get_django_choices(),
    )
    gateway_name = serializers.CharField(help_text="网关名称，用于记录操作记录")


class ESBPermissionRenewSLZ(serializers.Serializer):
    component_ids = serializers.ListField(
        child=serializers.IntegerField(),
    )
    expire_days = serializers.ChoiceField(
        choices=constants.PermissionApplyExpireDaysEnum.get_django_choices(),
    )


class ESBPermissionApplyRecordSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    bk_app_code = serializers.CharField()
    applied_by = serializers.CharField()
    applied_time = serializers.CharField()
    handled_by = serializers.CharField()
    handled_time = serializers.CharField()
    apply_status = serializers.ChoiceField(
        choices=constants.ApplyStatusEnum.get_django_choices(),
    )
    comment = serializers.CharField()
    reason = serializers.CharField()
    expire_days = serializers.IntegerField()
    system_name = serializers.CharField()


class ESBComponentApplyStatusSLZ(serializers.Serializer):
    name = serializers.CharField()
    apply_status = serializers.ChoiceField(
        choices=constants.ApplyStatusEnum.get_django_choices(),
    )


class ESBPermissionApplyRecordDetailSLZ(ESBPermissionApplyRecordSLZ):
    components = serializers.ListField(child=ESBComponentApplyStatusSLZ())
