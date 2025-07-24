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
from typing import Dict, Optional, Type

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.serializers import UniqueTogetherValidator

from paas_wl.workloads.networking.entrance.constants import AddressType
from paas_wl.workloads.networking.ingress.models import Domain
from paasng.platform.applications.models import Application


# Custom Domain(end-user) serializers start
class DomainEditableMixin(serializers.Serializer):
    """A collection of editable fields for Domain"""

    path_prefix = serializers.RegexField(
        r"^/([^/]+/?)*$",
        default="/",
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text='支持多级子目录，格式: "/path/" 或 "/path/subpath/"',
    )
    domain_name = serializers.RegexField(
        re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+\.?$"),
        max_length=253,
        required=True,
        error_messages={"invalid": _("域名格式错误")},
        source="name",
        help_text="域名",
    )
    https_enabled = serializers.BooleanField(required=False, default=False, help_text="是否开启HTTPS")

    class Meta:
        validators = [
            UniqueTogetherValidator(
                queryset=Domain.objects.all(),
                fields=("domain_name", "path_prefix"),
                message=_("该域名与路径组合已被其他应用或模块使用"),
            ),
        ]

    def validate_path_prefix(self, value) -> str:
        """Process path_prefix, transform to standard format '/subpath/'"""
        if not value:
            return "/"
        return value.rstrip("/") + "/"


class DomainSLZ(DomainEditableMixin):
    """For creation and representation"""

    id = serializers.IntegerField(read_only=True, help_text="记录 ID，仅供展示")
    module_name = serializers.CharField(source="module.name", help_text="模块名")
    environment_name = serializers.ChoiceField(
        source="environment.environment", choices=("stag", "prod"), required=True, help_text="环境"
    )


class DomainForUpdateSLZ(DomainEditableMixin):
    """For updating Domain"""


def validate_domain_payload(
    data: Dict,
    application: Application,
    serializer_cls: Type[serializers.Serializer],
    instance: Optional[Domain] = None,
):
    """Validate a domain data, which was read form user input

    :param application: The application which domain belongs to
    :param instance: Optional Domain object, must provide when perform updating
    :param serializer_slz: Optional serializer type, if not given, use DomainSLZ
    """
    serializer = serializer_cls(
        data=data,
        instance=instance,
    )
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# Custom Domain(end-user) serializers end
class AvailableEntranceSLZ(serializers.Serializer):
    id = serializers.IntegerField(help_text="记录 ID, 只有独立域名地址有效", required=False, allow_null=True)
    url = serializers.URLField(required=True)
    type = serializers.ChoiceField(
        choices=AddressType.get_choices(),
        required=True,
        help_text=" ".join(map(str, AddressType.get_choices())),
    )


class ModuleEnvAddressSLZ(serializers.Serializer):
    """模块环境访问地址"""

    module = serializers.CharField(help_text="模块名")
    env = serializers.CharField(help_text="环境名")
    address = AvailableEntranceSLZ(help_text="访问地址", allow_null=True)
    is_running = serializers.BooleanField(help_text="该环境是否正在运行", default=True)


class ModuleEntrancesSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="模块名")
    is_default = serializers.BooleanField(help_text="是否主模块")
    envs = serializers.DictField(child=ModuleEnvAddressSLZ(many=True))


class CustomDomainsConfigSLZ(serializers.Serializer):
    module = serializers.CharField(help_text="所属模块")
    environment = serializers.CharField(help_text="部署环境")
    frontend_ingress_ip = serializers.CharField(
        help_text='独立域名应该指向的地址，为空字符串 "" 时表示不支持独立域名功能'
    )


class SwitchMarketEntranceSLZ(serializers.Serializer):
    """切换市场访问地址"""

    module = serializers.CharField(help_text="切换模块名")
    address = AvailableEntranceSLZ(help_text="访问地址")
