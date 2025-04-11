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
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.core.tenant.constants import AppTenantMode
from paasng.utils.validators import Base64Validator


class LightAppCreateSLZ(serializers.Serializer):
    parent_app_code = serializers.CharField(required=True, help_text="父应用ID")
    app_name = serializers.CharField(
        required=True, allow_blank=False, max_length=20, help_text="轻应用名称", source="name"
    )
    app_tenant_mode = serializers.ChoiceField(
        help_text="应用租户模式", choices=AppTenantMode.get_choices(), default=None
    )
    app_tenant_id = serializers.CharField(
        required=False, default="", help_text="租户ID，全租户应用则租户 ID 为空字符串"
    )
    app_url = serializers.URLField(required=True, allow_blank=False, help_text="应用链接", source="external_url")
    developers = serializers.ListField(
        required=True, min_length=1, child=serializers.CharField(allow_blank=False), help_text="应用开发者用户名"
    )
    app_tag = serializers.CharField(
        required=False,
        default="Other",
        help_text=(
            "应用分类，可选分类： "
            '"OpsTools"（运维工具），'
            '"MonitorAlarm"（监控告警），'
            '"ConfManage"（配置管理），'
            '"DevTools"（开发工具），'
            '"EnterpriseIT"（企业IT），'
            '"OfficeApp"（办公应用），'
            '"Other"（其它）。'
            '如果传入空参数或不是上诉分类，则使用 "Other"'
        ),
        source="tag",
    )
    creator = serializers.CharField(required=True, help_text="创建者")
    logo = serializers.CharField(required=False, help_text="base64 编码的 logo 文件", validators=[Base64Validator()])
    introduction = serializers.CharField(required=False, default="-", help_text="应用的简介")
    width = serializers.IntegerField(required=False, default=None, help_text="应用在桌面打开窗口宽度")
    height = serializers.IntegerField(required=False, default=None, help_text="应用在桌面打开窗口高度")

    def validate(self, data):
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return data
        # 多租户模式下需要校验租户相关字段
        if data["app_tenant_mode"] == AppTenantMode.GLOBAL:
            if data["app_tenant_id"]:
                raise ValidationError(_("全租户应用的 app_tenant_id 必须为空"))
        elif not data["app_tenant_id"]:
            raise ValidationError(_("单租户应用必须设置 app_tenant_id"))
        return data


class LightAppDeleteSLZ(serializers.Serializer):
    light_app_code = serializers.CharField(required=True, help_text="轻应用ID")


class LightAppEditSLZ(serializers.Serializer):
    light_app_code = serializers.CharField(required=True, help_text="轻应用ID", source="code")
    app_name = serializers.CharField(
        required=False, allow_blank=False, max_length=20, help_text="轻应用名称", source="name"
    )
    app_url = serializers.URLField(required=False, allow_blank=False, help_text="应用链接", source="external_url")
    developers = serializers.ListField(
        required=False, min_length=1, child=serializers.CharField(allow_blank=False), help_text="应用开发者用户名"
    )
    app_tag = serializers.CharField(
        required=False,
        default="Other",
        help_text=(
            "应用分类，可选分类： "
            '"OpsTools"（运维工具），'
            '"MonitorAlarm"（监控告警），'
            '"ConfManage"（配置管理），'
            '"DevTools"（开发工具），'
            '"EnterpriseIT"（企业IT），'
            '"OfficeApp"（办公应用），'
            '"Other"（其它）。'
            '如果传入空参数或不是上诉分类，则使用 "Other"'
        ),
        source="tag",
    )
    logo = serializers.CharField(required=False, help_text="base64 编码的 logo 文件", validators=[Base64Validator()])
    introduction = serializers.CharField(required=False, default="", help_text="应用的简介")
    width = serializers.IntegerField(required=False, default=None, help_text="应用在桌面打开窗口宽度")
    height = serializers.IntegerField(required=False, default=None, help_text="应用在桌面打开窗口高度")


class LightAppQuerySLZ(serializers.Serializer):
    light_app_code = serializers.CharField(required=True, help_text="轻应用ID")
