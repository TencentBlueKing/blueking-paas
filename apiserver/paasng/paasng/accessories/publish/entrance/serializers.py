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
from rest_framework.exceptions import ValidationError

from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.serializers import MinimalModuleSLZ
from paasng.accessories.publish.market.serializers import AvailableAddressFullySLZ, AvailableAddressSLZ


class UpdateExposedURLTypeSLZ(serializers.Serializer):
    exposed_url_type = serializers.IntegerField(help_text="访问地址类型", required=True)

    def validate_exposed_url_type(self, value):
        if value != ExposedURLType.SUBDOMAIN:
            raise ValidationError(_('类型错误，只允许修改为子域名类型'))
        return value


class ApplicationCustomDomainEntranceSLZ(serializers.Serializer):
    module = MinimalModuleSLZ(help_text="模块信息")
    env = serializers.CharField(help_text="环境信息")
    addresses = AvailableAddressFullySLZ(many=True, help_text="地址列表", allow_null=True)


class ApplicationDefaultEntranceSLZ(serializers.Serializer):
    module = MinimalModuleSLZ(help_text="模块信息")
    env = serializers.CharField(help_text="环境信息")
    address = AvailableAddressSLZ(help_text="平台提供的访问地址", allow_null=True)


class PlainEntranceSLZ(serializers.Serializer):
    env = serializers.CharField(help_text="环境信息")
    address = serializers.URLField(required=True)
    is_running = serializers.BooleanField(help_text="该环境是否正在运行", default=True)


class ApplicationAvailableEntranceSLZ(serializers.Serializer):
    type = serializers.IntegerField()
    entrances = PlainEntranceSLZ(many=True)


class RootDoaminSLZ(serializers.Serializer):
    root_domains = serializers.ListField(help_text="查看模块所属集群的子域名根域", child=serializers.CharField(), default=[])
    preferred_root_domain = serializers.CharField(help_text="偏好的根域名", default="")


class PreferredRootDoaminSLZ(serializers.Serializer):
    preferred_root_domain = serializers.CharField(help_text="偏好的根域名", required=True)
