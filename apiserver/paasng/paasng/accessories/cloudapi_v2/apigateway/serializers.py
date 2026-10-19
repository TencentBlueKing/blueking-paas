# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paasng.accessories.cloudapi.constants import (
    ApplyStatusEnum,
    GrantDimensionEnum,
    PermissionApplyExpireDaysEnum,
)
from paasng.accessories.cloudapi_v2.constants import AlarmRecordStatus

# ============ 网关 API 相关 ============


# ------------ list_gateways ------------
class ListGatewaysInputSLZ(serializers.Serializer):
    """网关列表查询参数"""

    name = serializers.CharField(required=False, allow_blank=True, help_text="网关名称")
    fuzzy = serializers.BooleanField(required=False, default=True, help_text="是否模糊匹配")


class ListGatewaysOutputSLZ(serializers.Serializer):
    """网关信息"""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    maintainers = serializers.ListField(child=serializers.CharField(), required=False)
    doc_maintainers = serializers.JSONField(required=False)


# ------------ get_gateway ------------
class GetGatewayOutputSLZ(serializers.Serializer):
    """网关详情"""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    maintainers = serializers.ListField(child=serializers.CharField(), required=False)
    doc_maintainers = serializers.JSONField(required=False)


# ------------ list_gateway_permission_resources ------------
class ListGatewayPermissionResourcesInputSLZ(serializers.Serializer):
    """网关资源列表查询参数"""

    keyword = serializers.CharField(required=False, help_text="资源名称关键字")


class ListGatewayPermissionResourcesOutputSLZ(serializers.Serializer):
    """网关资源权限信息"""

    id = serializers.IntegerField(read_only=True, help_text="资源 ID")
    name = serializers.CharField(help_text="资源名称")
    gateway_name = serializers.CharField(help_text="网关名称")
    gateway_id = serializers.IntegerField(required=False, allow_null=True)
    description = serializers.CharField(allow_blank=True, allow_null=True)
    description_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    expires_in = serializers.IntegerField(allow_null=True, help_text="过期时间(秒)")
    permission_level = serializers.CharField(help_text="权限级别")
    permission_status = serializers.CharField(help_text="权限状态")
    permission_action = serializers.CharField(help_text="可执行操作")
    doc_link = serializers.CharField(allow_blank=True, help_text="文档链接")


# ------------ check_is_allowed_apply_by_gateway ------------
class CheckIsAllowedApplyByGatewayOutputSLZ(serializers.Serializer):
    """是否允许按网关申请权限"""

    allow_apply_by_gateway = serializers.BooleanField(read_only=True)
    reason = serializers.CharField(read_only=True, allow_blank=True)


# ------------ apply_gateway_resource_permission ------------
class ApplyGatewayResourcePermissionInputSLZ(serializers.Serializer):
    """网关资源权限申请参数"""

    resource_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
        required=False,
        help_text="资源 ID 列表，为空则按网关申请",
    )
    reason = serializers.CharField(max_length=512, allow_blank=True, required=False, default="", help_text="申请原因")
    expire_days = serializers.ChoiceField(
        choices=PermissionApplyExpireDaysEnum.get_django_choices(), help_text="有效期"
    )
    grant_dimension = serializers.ChoiceField(
        choices=GrantDimensionEnum.get_django_choices(), help_text="授权维度: api/resource"
    )


class ApplyGatewayResourcePermissionOutputSLZ(serializers.Serializer):
    """网关资源权限申请结果"""

    record_id = serializers.IntegerField(read_only=True, help_text="申请记录 ID")


# ------------ list_app_resource_permissions ------------
class ListAppResourcePermissionsOutputSLZ(serializers.Serializer):
    """应用资源权限信息"""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    gateway_name = serializers.CharField()
    gateway_id = serializers.IntegerField(required=False, allow_null=True)
    description = serializers.CharField(allow_blank=True, allow_null=True)
    description_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    expires_in = serializers.IntegerField(allow_null=True)
    permission_level = serializers.CharField()
    permission_status = serializers.CharField()
    permission_action = serializers.CharField()
    doc_link = serializers.CharField(allow_blank=True)


# ------------ renew_resource_permission ------------
class RenewResourcePermissionInputSLZ(serializers.Serializer):
    """资源权限续期参数"""

    resource_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False, required=True, max_length=100, help_text="资源 ID 列表"
    )
    expire_days = serializers.ChoiceField(
        choices=PermissionApplyExpireDaysEnum.get_django_choices(), help_text="有效期"
    )


# ------------ list_resource_permission_apply_records ------------
class ListResourcePermissionApplyRecordsInputSLZ(serializers.Serializer):
    """权限申请记录查询参数"""

    applied_by = serializers.CharField(allow_blank=True, required=False, help_text="申请人")
    applied_time_start = serializers.IntegerField(allow_null=True, required=False, help_text="申请开始时间(时间戳)")
    applied_time_end = serializers.IntegerField(allow_null=True, required=False, help_text="申请结束时间(时间戳)")
    apply_status = serializers.ChoiceField(
        choices=ApplyStatusEnum.get_django_choices(), allow_blank=True, required=False, help_text="申请状态"
    )
    query = serializers.CharField(allow_blank=True, required=False, help_text="搜索关键字")
    limit = serializers.IntegerField(default=10, required=False)
    offset = serializers.IntegerField(default=0, required=False)


class PermissionApplyRecordOutputSLZ(serializers.Serializer):
    """权限申请记录"""

    id = serializers.IntegerField()
    bk_app_code = serializers.CharField()
    applied_by = serializers.CharField()
    applied_time = serializers.CharField(help_text="申请时间")
    handled_by = serializers.ListField(child=serializers.CharField(), required=False)
    handled_time = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text="处理时间")
    apply_status = serializers.CharField()
    apply_status_display = serializers.CharField(required=False)
    grant_dimension = serializers.CharField(required=False)
    comment = serializers.CharField(allow_blank=True, required=False)
    reason = serializers.CharField(allow_blank=True, required=False)
    expire_days = serializers.IntegerField(required=False)
    gateway_name = serializers.CharField(required=False)
    approval_url = serializers.SerializerMethodField(help_text="审批链接")

    def get_approval_url(self, obj) -> str:
        """优先使用 approval_url，为空时回退到网关返回的 itsm_ticket_url"""
        if not isinstance(obj, dict):
            return ""
        return obj.get("approval_url") or obj.get("itsm_ticket_url") or ""


class PaginatedPermissionApplyRecordOutputSLZ(serializers.Serializer):
    """分页权限申请记录"""

    count = serializers.IntegerField()
    results = PermissionApplyRecordOutputSLZ(many=True)


# ------------ retrieve_resource_permission_apply_record ------------
class ResourceInRecordOutputSLZ(serializers.Serializer):
    """申请记录中的资源"""

    name = serializers.CharField()
    apply_status = serializers.CharField()


class RetrieveResourcePermissionApplyRecordOutputSLZ(PermissionApplyRecordOutputSLZ):
    """权限申请记录详情"""

    resources = ResourceInRecordOutputSLZ(many=True, required=False)


# ============ ESB 组件 API 相关 ============


# ------------ list_esb_systems ------------
class ListESBSystemsInputSLZ(serializers.Serializer):
    """ESB 系统列表查询参数"""

    keyword = serializers.CharField(required=False, help_text="系统名称关键字")


class ESBSystemOutputSLZ(serializers.Serializer):
    """ESB 系统信息"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, allow_null=True)
    maintainers = serializers.ListField(child=serializers.CharField(), required=False)
    tag = serializers.CharField(required=False, allow_blank=True)


# ------------ list_esb_system_permission_components ------------
class ListESBSystemPermissionComponentsInputSLZ(serializers.Serializer):
    """ESB 组件列表查询参数"""

    keyword = serializers.CharField(required=False, help_text="组件名称关键字")


class ESBComponentOutputSLZ(serializers.Serializer):
    """ESB 组件权限信息"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, allow_null=True)
    description_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    system_name = serializers.CharField(required=False)
    system_id = serializers.IntegerField(required=False, allow_null=True)
    permission_level = serializers.CharField(required=False)
    permission_status = serializers.CharField(required=False)
    permission_action = serializers.CharField(required=False)
    expires_in = serializers.IntegerField(required=False, allow_null=True)
    doc_link = serializers.CharField(required=False, allow_blank=True)
    tag = serializers.CharField(required=False, allow_blank=True)


# ------------ apply_esb_system_component_permissions ------------
class ApplyESBSystemComponentPermissionsInputSLZ(serializers.Serializer):
    """ESB 组件权限申请参数"""

    component_ids = serializers.ListField(child=serializers.IntegerField(), help_text="组件 ID 列表")
    reason = serializers.CharField(max_length=512, allow_blank=True, required=False, default="", help_text="申请原因")
    expire_days = serializers.ChoiceField(
        choices=PermissionApplyExpireDaysEnum.get_django_choices(), help_text="有效期"
    )


class ApplyESBSystemComponentPermissionsOutputSLZ(serializers.Serializer):
    """ESB 组件权限申请结果"""

    record_id = serializers.IntegerField(read_only=True)


# ------------ renew_esb_component_permissions ------------
class RenewESBComponentPermissionsInputSLZ(serializers.Serializer):
    """ESB 组件权限续期参数"""

    component_ids = serializers.ListField(child=serializers.IntegerField(), help_text="组件 ID 列表")
    expire_days = serializers.ChoiceField(
        choices=PermissionApplyExpireDaysEnum.get_django_choices(), help_text="有效期"
    )


# ------------ list_app_esb_component_permission_apply_records ------------
class ListAppESBComponentPermissionApplyRecordsInputSLZ(serializers.Serializer):
    """ESB 组件权限申请记录查询参数"""

    applied_by = serializers.CharField(allow_blank=True, required=False, help_text="申请人")
    applied_time_start = serializers.IntegerField(allow_null=True, required=False, help_text="申请开始时间(时间戳)")
    applied_time_end = serializers.IntegerField(allow_null=True, required=False, help_text="申请结束时间(时间戳)")
    apply_status = serializers.ChoiceField(
        choices=ApplyStatusEnum.get_django_choices(), allow_blank=True, required=False, help_text="申请状态"
    )
    query = serializers.CharField(allow_blank=True, required=False, help_text="搜索关键字")
    limit = serializers.IntegerField(default=10, required=False)
    offset = serializers.IntegerField(default=0, required=False)


class ComponentInRecordOutputSLZ(serializers.Serializer):
    """申请记录中的组件"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, allow_null=True)
    description_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    apply_status = serializers.CharField()


class ESBComponentPermissionApplyRecordOutputSLZ(serializers.Serializer):
    """ESB 组件权限申请记录"""

    id = serializers.IntegerField()
    bk_app_code = serializers.CharField()
    applied_by = serializers.CharField()
    applied_time = serializers.CharField(help_text="申请时间")
    handled_by = serializers.ListField(child=serializers.CharField(), required=False)
    handled_time = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text="处理时间")
    apply_status = serializers.CharField()
    apply_status_display = serializers.CharField(required=False)
    comment = serializers.CharField(allow_blank=True, required=False)
    reason = serializers.CharField(allow_blank=True, required=False)
    expire_days = serializers.IntegerField(required=False)
    system_name = serializers.CharField(required=False)
    tag = serializers.CharField(required=False, allow_blank=True)
    components = ComponentInRecordOutputSLZ(many=True, required=False)


class PaginatedESBComponentPermissionApplyRecordOutputSLZ(serializers.Serializer):
    """分页 ESB 组件权限申请记录"""

    count = serializers.IntegerField()
    results = ESBComponentPermissionApplyRecordOutputSLZ(many=True)


# ------------ get_app_esb_component_permission_apply_record ------------
class GetAppESBComponentPermissionApplyRecordOutputSLZ(ESBComponentPermissionApplyRecordOutputSLZ):
    """ESB 组件权限申请记录详情"""


# ============ 应用告警记录相关 ============


# ------------ list_app_alarm_records ------------
class ListAppAlarmRecordsInputSLZ(serializers.Serializer):
    """应用告警记录查询参数"""

    status = serializers.ChoiceField(
        choices=AlarmRecordStatus.get_choices(), required=False, allow_blank=True, help_text="告警状态"
    )
    gateway_name = serializers.CharField(required=False, allow_blank=True, help_text="网关名称")
    resource_name = serializers.CharField(required=False, allow_blank=True, help_text="资源名称")
    time_start = serializers.IntegerField(required=True, help_text="起始时间(Unix 时间戳, 秒)")
    time_end = serializers.IntegerField(required=True, help_text="结束时间(Unix 时间戳, 秒)")
    offset = serializers.IntegerField(required=False, default=0, min_value=0, help_text="偏移量")
    limit = serializers.IntegerField(required=False, default=10, min_value=1, max_value=100, help_text="每页条数")

    def validate(self, attrs: dict) -> dict:
        """校验查询条件

        - time_end 必须大于 time_start
        - time_end 若为未来时间, 截断为当前时间
        - 传 resource_name 时必须同时传 gateway_name
        """
        time_start = attrs["time_start"]
        now = int(timezone.now().timestamp())
        time_end = min(attrs["time_end"], now)

        if time_end <= time_start:
            raise serializers.ValidationError(_("结束时间必须大于起始时间"))

        if attrs.get("resource_name") and not attrs.get("gateway_name"):
            raise serializers.ValidationError({"gateway_name": _("传 resource_name 时，必须同时传 gateway_name")})

        attrs["time_end"] = time_end
        return attrs


class AppAlarmRecordOutputSLZ(serializers.Serializer):
    """应用告警记录"""

    id = serializers.IntegerField(help_text="告警记录 ID")
    alarm_id = serializers.CharField(required=False, help_text="告警平台事件 ID")
    status = serializers.CharField(required=False, help_text="告警状态")
    status_display = serializers.SerializerMethodField(help_text="告警状态描述")
    created_time = serializers.CharField(required=False, help_text="告警创建时间")
    gateway_name = serializers.CharField(required=False, help_text="网关名称")
    stage = serializers.CharField(required=False, help_text="环境")
    resource_id = serializers.IntegerField(required=False, allow_null=True, help_text="资源 ID")
    resource_name = serializers.CharField(required=False, help_text="资源名称")
    request_id = serializers.CharField(required=False, help_text="请求 ID")
    message = serializers.CharField(required=False, help_text="告警消息")

    def get_status_display(self, obj) -> str:
        """优先使用网关返回的 status_display, 缺失时按告警状态回退到本地枚举文案"""
        if not isinstance(obj, dict):
            return ""
        return obj.get("status_display") or AlarmRecordStatus.get_choice_label(obj.get("status") or "")


class ListAppAlarmRecordsOutputSLZ(serializers.Serializer):
    """应用告警记录列表"""

    count = serializers.IntegerField(default=0, help_text="总条数")
    results = AppAlarmRecordOutputSLZ(many=True, default=list, help_text="告警记录列表")
