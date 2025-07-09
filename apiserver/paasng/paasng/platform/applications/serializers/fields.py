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

import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paasng.core.tenant.user import get_tenant
from paasng.platform.applications.models import Application
from paasng.utils.serializers import NickNameField, SafePathField
from paasng.utils.validators import RE_APP_CODE, DnsSafeNameValidator, ReservedWordValidator

from .validators import AppIDUniqueValidator, AppNameUniqueValidator


class AppIDField(serializers.RegexField):
    """Field for validating application ID"""

    def __init__(self, regex=RE_APP_CODE, *args, **kwargs):
        preset_kwargs = dict(
            max_length=16,
            min_length=3,
            required=True,
            help_text="应用 ID",
            validators=[
                ReservedWordValidator(_("应用 ID")),
                DnsSafeNameValidator(_("应用 ID")),
                AppIDUniqueValidator(),
            ],
            error_messages={
                "invalid": _("格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)，长度在 3-16 之间。")
            },
        )
        preset_kwargs.update(kwargs)
        super().__init__(regex, *args, **preset_kwargs)


class AppIDSMartField(serializers.RegexField):
    """Field for validating S-mart applications's ID, the differences to `AppIDField`:

    - max length increased from 16 to 20
    - allow using underscore("_")
    """

    # A variation of the DNS pattern with "_" allowed
    pattern = re.compile(r"^(?![0-9]+.*$)(?!-)[a-zA-Z0-9-_]{,63}(?<!-)$")

    def __init__(self, *args, **kwargs):
        preset_kwargs = dict(
            max_length=20,
            min_length=3,
            required=True,
            help_text="应用 ID",
            validators=[ReservedWordValidator(_("应用 ID")), AppIDUniqueValidator()],
            error_messages={
                "invalid": _(
                    "格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)和下划线(_)，长度在 3-20 之间。"
                )
            },
        )
        preset_kwargs.update(kwargs)
        super().__init__(self.pattern, *args, **preset_kwargs)


class ApplicationField(serializers.SlugRelatedField):
    def get_queryset(self):
        user = self.context["request"].user
        return Application.objects.filter_by_user(user=user, tenant_id=get_tenant(user).id)


class AppNameField(NickNameField):
    """Field for validating application name"""

    def __init__(self, *args, **kwargs):
        preset_kwargs = dict(max_length=20, help_text="应用名称", validators=[AppNameUniqueValidator()])
        preset_kwargs.update(kwargs)
        super().__init__(*args, **preset_kwargs)


class SourceDirField(SafePathField):
    """Field for validating source directory"""

    default_error_messages = {
        "invalid": _("构建目录 {path} 不合法"),
        "escape_risk": _("构建目录 {path} 存在逃逸风险"),
    }

    def __init__(self, **kwargs):
        preset_kwargs = dict(max_length=255, default="", allow_blank=True)
        preset_kwargs.update(kwargs)
        super().__init__(**preset_kwargs)


class DockerfilePathField(SafePathField):
    """Field for validating Dockerfile path"""

    default_error_messages = {
        "invalid": _("Dockerfile 目录 {path} 不合法"),
        "escape_risk": _("Dockerfile 目录 {path} 存在逃逸风险"),
    }

    def __init__(self, **kwargs):
        preset_kwargs = dict(max_length=255, allow_blank=True, allow_null=True)
        preset_kwargs.update(kwargs)
        super().__init__(**preset_kwargs)
