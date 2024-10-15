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

from paasng.platform.declarative.application.validations.v2 import MarketSLZ, ModuleDescriptionSLZ
from paasng.platform.declarative.constants import DiffType
from paasng.utils.i18n.serializers import TranslatedCharField


class AppDescriptionSLZ(serializers.Serializer):
    """Represent application description object only"""

    region = serializers.CharField()
    code = serializers.CharField()
    name = TranslatedCharField()
    # NOTE: 必须使用 market.dict, 以去除 OmittedType
    market = MarketSLZ(required=False, default=None, source="market.dict")
    modules = serializers.DictField(child=ModuleDescriptionSLZ())


class PackageStashRequestSLZ(serializers.Serializer):
    """Handle S-mart application uploads"""

    package = serializers.FileField(help_text="应用源码包")

    def validate_package(self, package):
        if not re.fullmatch("[a-zA-Z0-9-_. ]+", package.name):
            raise serializers.ValidationError(
                {"invalid": _("格式错误，只能包含字母(a-zA-Z)、数字(0-9)和半角连接符(-)、下划线(_)、空格( )和点(.)")}
            )
        return package


class PackageStashResponseSLZ(serializers.Serializer):
    app_description = AppDescriptionSLZ()
    signature = serializers.CharField(help_text="数字签名")
    supported_services = serializers.ListField(child=serializers.CharField(), help_text="支持的增强服务")


class DiffItemSLZ(serializers.Serializer):
    resource = serializers.JSONField()
    diff_type = serializers.ChoiceField(choices=DiffType.get_choices())


class DescriptionDiffResultSLZ(serializers.Serializer):
    services = serializers.ListField(child=DiffItemSLZ())
