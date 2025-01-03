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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.shim import RegionClusterService
from paasng.core.region.states import get_region
from paasng.core.tenant.constants import AppTenantMode
from paasng.utils.i18n.serializers import I18NExtend, i18n

from .fields import AppIDField, AppNameField


@i18n
class AppBasicInfoMixin(serializers.Serializer):
    region = serializers.ChoiceField(choices=get_region().get_choices())
    code = AppIDField()
    name = I18NExtend(AppNameField())
    app_tenant_mode = serializers.ChoiceField(
        help_text="应用租户模式", choices=AppTenantMode.get_choices(), default=None
    )


class MarketParamsMixin(serializers.Serializer):
    """蓝鲸市场相关参数"""

    source_tp_url = serializers.URLField(required=False, allow_blank=True, help_text="第三方访问地址")


class AdvancedCreationParamsMixin(serializers.Serializer):
    """高级应用创建选项"""

    cluster_name = serializers.CharField(required=False)

    def validate_cluster_name(self, value: str) -> str:
        # Get region value from parent serializer
        region = self.parent.initial_data["region"]
        if not RegionClusterService(region).has_cluster(value):
            raise ValidationError(_("集群名称错误，无法找到名为 {value} 的集群").format(value=value))
        return value
