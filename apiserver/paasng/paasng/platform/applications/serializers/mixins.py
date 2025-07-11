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

from typing import Any, Dict

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import get_tenant
from paasng.core.tenant.utils import stub_app_tenant_info, validate_app_tenant_info
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.applications.serializers.fields import AppIDField, AppNameField
from paasng.utils.i18n.serializers import I18NExtend, i18n


@i18n
class AppBasicInfoMixin(serializers.Serializer):
    code = AppIDField()
    name = I18NExtend(AppNameField())
    app_tenant_mode = serializers.ChoiceField(
        help_text="应用租户模式", choices=AppTenantMode.get_choices(), default=None
    )


class MarketParamsMixin(serializers.Serializer):
    """蓝鲸市场相关参数"""

    source_tp_url = serializers.URLField(required=False, allow_blank=True, help_text="第三方访问地址")


class EnvClusterNamesSLZ(serializers.Serializer):
    stag = serializers.CharField(help_text="预发布环境集群名称")
    prod = serializers.CharField(help_text="生产环境集群名称")

    def validate_stag(self, name: str) -> str:
        return self._validate(name, AppEnvironment.STAGING)

    def validate_prod(self, name: str) -> str:
        return self._validate(name, AppEnvironment.PRODUCTION)

    def _validate(self, name: str, environment: AppEnvironment) -> str:
        cur_user = self.context["user"]

        ctx = AllocationContext(
            tenant_id=get_tenant(cur_user).id,
            region=self.parent.parent.initial_data["region"],
            environment=environment,
            username=cur_user.username,
        )
        if not ClusterAllocator(ctx).check_available(name):
            raise ValidationError(_("集群名称错误，无法找到名为 {name} 的集群").format(name=name))

        return name


class AdvancedCreationParamsMixin(serializers.Serializer):
    """高级应用创建选项"""

    env_cluster_names = EnvClusterNamesSLZ(help_text="各环境集群名称", required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if not attrs:
            return attrs

        if not AccountFeatureFlag.objects.has_feature(self.context["user"], AFF.ALLOW_ADVANCED_CREATION_OPTIONS):
            raise ValidationError(_("你无法使用高级创建选项"))

        return attrs


class AppTenantMixin(serializers.Serializer):
    """应用的租户字段 app_tenant_mode 和 app_tenant_id"""

    app_tenant_mode = serializers.ChoiceField(
        help_text="应用租户模式", choices=AppTenantMode.get_choices(), default=None
    )
    app_tenant_id = serializers.CharField(
        required=False, default="", help_text="租户ID，全租户应用则租户 ID 为空字符串"
    )

    def validate(self, data):
        # 非多租户模式下，应用的租户信息由平台固定设置
        if not settings.ENABLE_MULTI_TENANT_MODE:
            app_tenant_info = stub_app_tenant_info()
        else:
            try:
                app_tenant_info = validate_app_tenant_info(data["app_tenant_mode"], data["app_tenant_id"])
            except ValueError as e:
                raise ValidationError(e)

        data["app_tenant_mode"] = app_tenant_info.app_tenant_mode
        data["app_tenant_id"] = app_tenant_info.app_tenant_id
        data["tenant_id"] = app_tenant_info.tenant_id
        return data
