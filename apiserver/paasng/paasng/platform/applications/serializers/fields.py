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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paasng.platform.applications.models import Application
from paasng.utils.serializers import NickNameField
from paasng.utils.validators import RE_APP_CODE, DnsSafeNameValidator, ReservedWordValidator

from .validators import AppIDUniqueValidator, AppNameUniqueValidator


class AppIDField(serializers.RegexField):
    """Field for validating application ID"""

    def __init__(self, regex=RE_APP_CODE, *args, **kwargs):
        preset_kwargs = dict(
            max_length=16,
            min_length=3,
            required=True,
            help_text='应用 ID',
            validators=[
                ReservedWordValidator(_("应用 ID")),
                DnsSafeNameValidator(_("应用 ID")),
                AppIDUniqueValidator(),
            ],
            error_messages={'invalid': _('格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)')},
        )
        preset_kwargs.update(kwargs)
        super().__init__(regex, *args, **preset_kwargs)


class ApplicationField(serializers.SlugRelatedField):
    def get_queryset(self):
        return Application.objects.filter_by_user(user=self.context["request"].user)


class AppNameField(NickNameField):
    """Field for validating application name"""

    def __init__(self, *args, **kwargs):
        preset_kwargs = dict(max_length=20, help_text='应用名称', validators=[AppNameUniqueValidator()])
        preset_kwargs.update(kwargs)
        super().__init__(*args, **preset_kwargs)
