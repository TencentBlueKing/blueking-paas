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

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.bk_app.monitoring.metrics.models import AppResourceUsageReport
from paasng.accessories.publish.market.models import MarketConfig
from paasng.accessories.publish.market.utils import MarketAvailableAddressHelper
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.utils.models import OrderByField
from paasng.utils.serializers import HumanizeDateTimeField, UserNameField

logger = logging.getLogger(__name__)


class ApplicationSLZ(serializers.ModelSerializer):
    region_name = serializers.CharField(read_only=True, source="get_region_display", help_text="region对应的中文名称")
    logo_url = serializers.CharField(read_only=True, source="get_logo_url", help_text="应用的Logo地址")
    config_info = serializers.DictField(read_only=True, help_text="应用额外状态信息")
    owner = UserNameField()
    creator = UserNameField()
    created_humanized = HumanizeDateTimeField(source="created")
    updated_humanized = HumanizeDateTimeField(source="updated")

    app_type = serializers.SerializerMethodField(read_only=True)
    resource_quotas = serializers.SerializerMethodField(read_only=True)

    def get_app_type(self, instance: Application) -> str:
        return ApplicationType.get_choice_label(instance.type)

    def get_resource_quotas(self, instance: Application) -> dict:
        default_quotas = {"memory": "--", "cpu": "--"}
        if app_resource_quotas := self.context.get("app_resource_quotas"):
            return app_resource_quotas.get(instance.code, default_quotas)
        return default_quotas

    class Meta:
        model = Application
        fields = "__all__"


class ApplicationDetailSLZ(ApplicationSLZ):
    modules = serializers.SerializerMethodField()
    market_availabled_address = serializers.SerializerMethodField()

    def get_modules(self, obj):
        # 将 default_module 排在第一位
        modules = obj.modules.all().order_by("-is_default", "-created")
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

    valid_order_by_fields = ("code", "created", "latest_operated_at")

    include_inactive = serializers.BooleanField(default=False, help_text="是否包括已下架应用")
    regions = serializers.ListField(required=False, help_text="应用 region")
    languages = serializers.ListField(required=False, help_text="应用开发语言")
    search_term = serializers.CharField(required=False, help_text="搜索关键字")
    source_origin = serializers.IntegerField(required=False, help_text="源码来源")
    market_enabled = serializers.NullBooleanField(required=False, default=None, help_text="是否已开启市场")
    order_by = serializers.ListField(default=["-created"], help_text="排序关键字")

    def validate_order_by(self, fields):
        for field in fields:
            f = OrderByField.from_string(field)
            if f.name not in self.valid_order_by_fields:
                raise ValidationError("无效的排序选项：%s" % f)
        return fields


class LegacyApplicationFilterSLZ(serializers.Serializer):
    only_include_legacy_v1_app = serializers.BooleanField(default=False, help_text="仅包括V1 PaaS应用")
    only_include_not_migrated_app = serializers.BooleanField(default=False, help_text="仅包括未迁移应用")
    include_downed_app = serializers.BooleanField(default=False, help_text="包括已下架应用")

    search_term = serializers.CharField(required=False, help_text="搜索关键字, 只搜索应用id")


class AppResourceUsageReportListInputSLZ(serializers.Serializer):
    """应用资源使用报告列表查询参数"""

    search_term = serializers.CharField(required=False, help_text="搜索关键字")
    order_by = serializers.CharField(help_text="排序字段", default="-mem_limits")


class AppResourceUsageReportOutputSLZ(serializers.Serializer):
    """应用资源使用报告"""

    app_code = serializers.CharField(help_text="应用 Code")
    app_name = serializers.CharField(help_text="应用名称")
    mem_requests = serializers.SerializerMethodField(help_text="内存请求量")
    mem_limits = serializers.SerializerMethodField(help_text="内存限制")
    mem_usage_avg = serializers.SerializerMethodField(help_text="内存平均使用率")
    cpu_requests = serializers.SerializerMethodField(help_text="CPU 请求量")
    cpu_limits = serializers.SerializerMethodField(help_text="CPU 限制")
    cpu_usage_avg = serializers.SerializerMethodField(help_text="CPU 平均使用率")
    pv = serializers.IntegerField(help_text="PV")
    uv = serializers.IntegerField(help_text="UV")
    summary = serializers.JSONField(help_text="汇总")
    operator = serializers.CharField(help_text="最近操作人")
    collected_at = serializers.DateTimeField(help_text="报告采集时间")

    def get_mem_requests(self, report: AppResourceUsageReport) -> str:
        return f"{round(report.mem_requests / 1024, 2)} G"

    def get_mem_limits(self, report: AppResourceUsageReport) -> str:
        return f"{round(report.mem_limits / 1024, 2)} G"

    def get_mem_usage_avg(self, report: AppResourceUsageReport) -> str:
        return f"{round(report.mem_usage_avg * 100, 2)}%"

    def get_cpu_requests(self, report: AppResourceUsageReport) -> str:
        return f"{round(report.cpu_requests / 1000, 2)} 核"

    def get_cpu_limits(self, report: AppResourceUsageReport) -> str:
        return f"{round(report.cpu_limits / 1000, 2)} 核"

    def get_cpu_usage_avg(self, report: AppResourceUsageReport) -> str:
        return f"{round(report.cpu_usage_avg * 100, 2)}%"
