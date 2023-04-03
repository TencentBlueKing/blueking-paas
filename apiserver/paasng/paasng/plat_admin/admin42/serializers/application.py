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
import logging
from collections import defaultdict
from dataclasses import dataclass

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.platform.applications.models import Application
from paasng.platform.applications.utils import get_processes_specs
from paasng.publish.market.models import MarketConfig
from paasng.publish.market.utils import MarketAvailableAddressHelper
from paasng.utils.models import OrderByField
from paasng.utils.serializers import HumanizeDateTimeField, UserNameField

logger = logging.getLogger(__name__)


@dataclass
class ResQuotasAggregation:
    app: Application

    def get_resource_quotas(self) -> dict:
        quotas: dict = {"prod": defaultdict(int), "stag": defaultdict(int)}
        for app_env in self.app.get_app_envs():
            processes_specs = get_processes_specs(self.app, app_env)

            for _specs in processes_specs:
                quotas[app_env.environment]["memory_total"] += (
                    _specs["resource_limit_quota"]['memory'] * _specs['target_replicas']
                )
                quotas[app_env.environment]["cpu_total"] += (
                    _specs["resource_limit_quota"]['cpu'] * _specs['target_replicas']
                )

        return quotas


class ApplicationSLZ(serializers.ModelSerializer):
    region_name = serializers.CharField(read_only=True, source='get_region_display', help_text=u"region对应的中文名称")
    logo_url = serializers.CharField(read_only=True, source='get_logo_url', help_text=u"应用的Logo地址")
    config_info = serializers.DictField(read_only=True, help_text='应用额外状态信息')
    owner = UserNameField()
    creator = UserNameField()
    created_humanized = HumanizeDateTimeField(source="created")
    updated_humanized = HumanizeDateTimeField(source="updated")

    resource_quotas = serializers.SerializerMethodField(read_only=True)

    def get_resource_quotas(self, instance: Application) -> dict:
        res_quotas = ResQuotasAggregation(instance).get_resource_quotas()

        # cpu 的单位从默认的 m 转为 核
        cpu = sum([v["cpu_total"] for v in res_quotas.values()]) // 1000
        # 内存的单位从默认的 Mi 转为 G
        memory = sum([v["memory_total"] for v in res_quotas.values()]) // 1024
        return {"cpu": cpu, "memory": memory}

    class Meta:
        model = Application
        fields = '__all__'


class ApplicationDetailSLZ(ApplicationSLZ):
    modules = serializers.SerializerMethodField()
    market_availabled_address = serializers.SerializerMethodField()

    def get_modules(self, obj):
        # 将 default_module 排在第一位
        modules = obj.modules.all().order_by('-is_default', '-created')
        return ModuleSLZ(modules, many=True).data

    def get_market_availabled_address(self, obj):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(obj)
        access_entrance = MarketAvailableAddressHelper(market_config).access_entrance
        if access_entrance:
            return access_entrance.address
        else:
            return None


class BindEnvClusterSLZ(serializers.Serializer):
    """绑定应用部署环境集群配置"""

    cluster_name = serializers.CharField(max_length=32)


class ApplicationFilterSLZ(serializers.Serializer):
    """Serializer for application query filter"""

    valid_order_by_fields = ('code', 'created', 'latest_operated_at')

    include_inactive = serializers.BooleanField(default=False, help_text="是否包括已下架应用")
    regions = serializers.ListField(required=False, help_text='应用 region')
    languages = serializers.ListField(required=False, help_text='应用开发语言')
    search_term = serializers.CharField(required=False, help_text='搜索关键字')
    source_origin = serializers.IntegerField(required=False, help_text="源码来源")
    market_enabled = serializers.NullBooleanField(required=False, default=None, help_text="是否已开启市场")
    order_by = serializers.ListField(default=['-created'], help_text='排序关键字')

    def validate_order_by(self, fields):
        for field in fields:
            f = OrderByField.from_string(field)
            if f.name not in self.valid_order_by_fields:
                raise ValidationError(u'无效的排序选项：%s' % f)
        return fields


class LegacyApplicationFilterSLZ(serializers.Serializer):
    only_include_legacy_v1_app = serializers.BooleanField(default=False, help_text="仅包括V1 PaaS应用")
    only_include_not_migrated_app = serializers.BooleanField(default=False, help_text="仅包括未迁移应用")
    include_downed_app = serializers.BooleanField(default=False, help_text="包括已下架应用")

    search_term = serializers.CharField(required=False, help_text='搜索关键字, 只搜索应用id')
