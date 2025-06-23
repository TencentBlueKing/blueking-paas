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

from typing import Dict, Optional

from django.conf import settings
from django.db.transaction import atomic
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.core.region.states import get_region
from paasng.platform.applications.constants import AppLanguage, ApplicationType, AvailabilityLevel
from paasng.platform.applications.exceptions import IntegrityError
from paasng.platform.applications.models import Application, UserMarkedApplication
from paasng.platform.applications.operators import get_last_operator
from paasng.platform.applications.signals import application_logo_updated, prepare_change_application_name
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models.module import Module
from paasng.platform.modules.serializers import MinimalModuleSLZ, ModuleSLZ
from paasng.utils.i18n.serializers import I18NExtend, TranslatedCharField, i18n
from paasng.utils.serializers import UserNameField
from paasng.utils.validators import RE_APP_SEARCH

from .fields import AppIDField, ApplicationField, AppNameField
from .mixins import AppTenantMixin


@i18n
class SysThirdPartyApplicationSLZ(AppTenantMixin):
    """创建系统外链应用"""

    region = serializers.ChoiceField(choices=get_region().get_choices())
    code = AppIDField()
    name = I18NExtend(AppNameField())
    operator = serializers.CharField(required=True)

    def validate_code(self, code):
        sys_id = self.context.get("sys_id")
        if sys_id not in settings.ALLOW_THIRD_APP_SYS_ID_LIST:
            raise ValidationError(f"系统({sys_id})未被允许创建外链应用")

        # 应用ID 必现以 "系统ID-" 为前缀
        prefix = f"{sys_id}-"
        if not code.startswith(prefix):
            raise ValidationError(f"应用ID 必须以 {prefix} 为前缀")
        return code


class TagOutputSLZ(serializers.Serializer):
    """Serializer for application tag output"""

    id = serializers.IntegerField(help_text="应用标签 ID")
    name = serializers.CharField(help_text="应用标签名称")


class AppExtraInfoOutputSLZ(serializers.Serializer):
    """Serializer for application extra info output"""

    availability_level = serializers.CharField(
        help_text="可用性保障等级", required=False, allow_null=True, allow_blank=True
    )
    tag = TagOutputSLZ(help_text="应用标签", required=False, allow_null=True)


@i18n
class UpdateApplicationNameSLZ(serializers.Serializer):
    """Serializer for update application name"""

    name = I18NExtend(AppNameField(max_length=20, help_text="应用名称"))

    def _validate_duplicated_field(self, data):
        """Universal validate method for code and name"""
        # Send signal, when console_db if given, this function call will raise
        # ValidationError if name is duplicated.
        # 仅修改对应语言的应用名称
        update_fields = {}
        if get_language() == "zh-cn":
            update_fields["name"] = data["name_zh_cn"]
        elif get_language() == "en":
            update_fields["name_en"] = data["name_en"]

        try:
            prepare_change_application_name.send(sender=self.__class__, code=self.instance.code, **update_fields)
        except IntegrityError as e:
            detail = {e.field: [_("{}已经被占用").format(e.get_field_display())]}
            raise ValidationError(detail=detail)
        return data

    def validate(self, data):
        return self._validate_duplicated_field(data)


class UpdateApplicationSLZ(UpdateApplicationNameSLZ):
    """Serializer for update application"""

    availability_level = serializers.ChoiceField(
        choices=AvailabilityLevel.get_choices(),
        help_text="可用性保障等级",
        required=False,
    )
    tag_id = serializers.IntegerField(help_text="应用标签 ID")


@i18n
class UpdateApplicationOutputSLZ(serializers.Serializer):
    name = I18NExtend(AppNameField(max_length=20, help_text="应用名称"))
    availability_level = serializers.CharField(source="extra_info.availability_level", help_text="可用性保障等级")
    tag_id = serializers.IntegerField(source="extra_info.tag.id", help_text="应用标签 ID")
    tag_name = serializers.CharField(source="extra_info.tag.name", help_text="应用标签名称")
    logo_url = serializers.CharField(source="get_logo_url", help_text="应用 Logo 访问地址")


class SearchApplicationSLZ(serializers.Serializer):
    keyword = serializers.RegexField(RE_APP_SEARCH, max_length=20, default="", allow_blank=False)
    include_inactive = serializers.BooleanField(default=False)
    prefer_marked = serializers.BooleanField(default=True)


class IdleModuleEnvSLZ(serializers.Serializer):
    module_name = serializers.CharField(help_text="模块名称")
    env_name = serializers.ChoiceField(help_text="环境", choices=AppEnvName.get_choices())
    cpu_quota = serializers.IntegerField(help_text="CPU 配额")
    memory_quota = serializers.IntegerField(help_text="内存配额")
    cpu_usage_avg = serializers.FloatField(help_text="CPU 平均使用率")
    # 注：环境的最近部署时间存储在 JSONField 中，在入库时已经转成字符串，不需要使用 DateTimeField
    latest_deployed_at = serializers.CharField(help_text="最近部署时间")


class IdleApplicationSLZ(serializers.Serializer):
    code = serializers.CharField(help_text="应用 Code")
    name = serializers.CharField(help_text="应用名称")
    type = serializers.CharField(help_text="应用类型")
    is_plugin_app = serializers.BooleanField(help_text="是否为插件应用")
    logo_url = serializers.CharField(help_text="应用 Logo 访问地址")

    administrators = serializers.JSONField(help_text="应用管理员列表")
    developers = serializers.JSONField(help_text="应用开发者列表")
    module_envs = serializers.ListField(help_text="闲置模块 & 环境列表", child=IdleModuleEnvSLZ())


class IdleApplicationListOutputSLZ(serializers.Serializer):
    collected_at = serializers.DateTimeField(help_text="采集时间")
    applications = serializers.ListField(help_text="应用列表", child=IdleApplicationSLZ())


class ApplicationEvaluationSLZ(serializers.Serializer):
    code = serializers.CharField(source="app.code", help_text="应用 Code")
    name = serializers.CharField(source="app.name", help_text="应用名称")
    type = serializers.CharField(source="app.type", help_text="应用类型")
    is_plugin_app = serializers.BooleanField(source="app.is_plugin_app", help_text="是否为插件应用")
    logo_url = serializers.CharField(source="app.get_logo_url", help_text="应用 Logo 访问地址")
    cpu_limits = serializers.IntegerField(help_text="CPU 配额")
    mem_limits = serializers.IntegerField(help_text="内存配额")
    cpu_usage_avg = serializers.FloatField(help_text="CPU 使用率(7d)")
    mem_usage_avg = serializers.FloatField(help_text="内存使用率(7d)")
    pv = serializers.IntegerField(help_text="PV(30d)")
    uv = serializers.IntegerField(help_text="UV(30d)")
    latest_operated_at = serializers.DateTimeField(help_text="最近操作时间")
    issue_type = serializers.ChoiceField(choices=OperationIssueType.get_choices(), help_text="应用状态")


class ApplicationEvaluationListQuerySLZ(serializers.Serializer):
    issue_type = serializers.ChoiceField(
        choices=OperationIssueType.get_choices(), help_text="应用状态", required=False, allow_null=True
    )
    order = serializers.CharField(help_text="排序", default="id")

    def validate_order(self, value):
        if value not in ["cpu_usage_avg", "-cpu_usage_avg", "pv", "-pv", "uv", "-uv", "id", "-id"]:
            raise ValidationError(_("排序字段不合法"))

        return value


class ApplicationEvaluationListResultSLZ(serializers.Serializer):
    collected_at = serializers.DateTimeField(help_text="采集时间")
    applications = serializers.ListField(help_text="应用列表", child=ApplicationEvaluationSLZ())


class ApplicationEvaluationIssueCountSLZ(serializers.Serializer):
    issue_type = serializers.ChoiceField(choices=OperationIssueType.get_choices(), help_text="评估结果类型")
    count = serializers.IntegerField(help_text="应用数量")


class ApplicationEvaluationIssueCountListResultSLZ(serializers.Serializer):
    collected_at = serializers.DateTimeField(help_text="采集时间")
    issue_type_counts = ApplicationEvaluationIssueCountSLZ(many=True, help_text="应用评估结果及数量")
    total = serializers.IntegerField(help_text="应用评估报告总数量")


class EnvironmentDeployInfoSLZ(serializers.Serializer):
    deployed = serializers.BooleanField(help_text="是否部署")
    url = serializers.URLField(help_text="访问地址")


class ApplicationSLZ(serializers.ModelSerializer):
    name = TranslatedCharField()
    region_name = serializers.CharField(read_only=True, source="get_region_display", help_text="应用版本名称")
    logo_url = serializers.CharField(read_only=True, source="get_logo_url", help_text="应用的 Logo 地址")
    config_info = serializers.DictField(read_only=True, help_text="应用的额外状态信息")
    modules = serializers.SerializerMethodField(help_text="应用各模块信息列表")
    extra_info = AppExtraInfoOutputSLZ(help_text="应用额外信息", read_only=True, allow_null=True)
    creator = UserNameField()
    owner = UserNameField()

    def get_modules(self, application: Application):
        # 将 default_module 排在第一位
        modules = application.modules.all().order_by("-is_default", "-created")
        return ModuleSLZ(modules, many=True).data

    class Meta:
        model = Application
        exclude = ["logo", "tenant_id"]


class ApplicationWithDeployInfoSLZ(ApplicationSLZ):
    deploy_info = serializers.JSONField(read_only=True, source="_deploy_info", help_text="部署状态")


class ApplicationRelationSLZ(serializers.Serializer):
    id = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField()

    def to_internal_value(self, data):
        """将属性转换为 validated_data 的方法， 直接将其赋值为 application 来通过验证"""
        return data


class ApplicationListDetailedSLZ(serializers.Serializer):
    """Serializer for detailed app list"""

    valid_order_by_fields = ("code", "created", "latest_operated_at", "name")
    exclude_collaborated = serializers.BooleanField(default=False)
    include_inactive = serializers.BooleanField(default=False)
    region = serializers.ListField(required=False)
    language = serializers.ListField(required=False)
    search_term = serializers.CharField(required=False)
    source_origin = serializers.ChoiceField(required=False, allow_null=True, choices=SourceOrigin.get_choices())
    type = serializers.ChoiceField(choices=ApplicationType.get_django_choices(), required=False)
    order_by = serializers.CharField(default="name")
    prefer_marked = serializers.BooleanField(default=True)
    app_tenant_mode = serializers.CharField(required=False)

    def validate_order_by(self, value):
        if value.startswith("-"):
            value = "-%s" % value.lstrip("-")

        if value.lstrip("-") not in self.valid_order_by_fields:
            raise ValidationError("无效的排序选项：%s" % value)
        return value

    @staticmethod
    def _validate_choice(value_list, choice):
        choice_key = [c[0] for c in choice]
        for value in value_list:
            if value not in choice_key:
                raise ValidationError(_("无效的选项: %s") % value)
        return value_list

    def validate_region(self, value_list):
        return self._validate_choice(value_list, get_region().get_choices())

    def validate_language(self, value_list):
        return self._validate_choice(value_list, AppLanguage.get_django_choices())

    def validate_source_origin(self, value: Optional[int]):
        if value:
            return SourceOrigin(value)
        return None

    def validate_type(self, value: Optional[str]):
        if value:
            return ApplicationType(value)
        return None


class ApplicationListMinimalSLZ(serializers.Serializer):
    include_inactive = serializers.BooleanField(default=False)
    source_origin = serializers.ChoiceField(
        choices=SourceOrigin.get_choices(), default=None, allow_blank=True, allow_null=True
    )


class ApplicationGroupFieldSLZ(serializers.Serializer):
    """Serializer for detailed app list"""

    include_inactive = serializers.BooleanField(default=False)
    field = serializers.CharField(default="region")

    def validate_field(self, value):
        if value not in ["region", "language"]:
            raise ValidationError(_("无效的分类选项: %s") % value)
        return value


class ProductSLZ(serializers.Serializer):
    name = serializers.CharField()
    logo = serializers.CharField(source="get_logo_url")


class MarketConfigSLZ(serializers.Serializer):
    # 第三方应用直接打开应用地址，不需要打开应用市场的地址
    source_tp_url = serializers.URLField(required=False, allow_blank=True, allow_null=True, help_text="第三方访问地址")


class ApplicationWithMarketSLZ(serializers.Serializer):
    application = ApplicationWithDeployInfoSLZ(read_only=True)
    product = ProductSLZ(read_only=True)
    marked = serializers.BooleanField(read_only=True)
    market_config = MarketConfigSLZ(read_only=True)
    migration_status = serializers.JSONField(read_only=True)


class ApplicationMinimalSLZ(serializers.ModelSerializer):
    name = TranslatedCharField()

    class Meta:
        model = Application
        fields = ["id", "code", "name"]


class ApplicationWithMarkMinimalSLZ(serializers.Serializer):
    """用于显示带收藏标记的应用列表"""

    application = ApplicationMinimalSLZ(read_only=True)
    marked = serializers.BooleanField(read_only=True)


class ApplicationSLZ4Record(serializers.ModelSerializer):
    """用于操作记录"""

    name = TranslatedCharField()
    logo_url = serializers.CharField(read_only=True, source="get_logo_url", help_text="应用的Logo地址")
    config_info = serializers.DictField(read_only=True, help_text="应用额外状态信息")

    class Meta:
        model = Application
        fields = ["id", "type", "code", "name", "logo_url", "config_info"]


class ApplicationWithLogoMinimalSLZ(serializers.ModelSerializer):
    """用于带Logo URL的简化应用列表"""

    name = TranslatedCharField()
    logo_url = serializers.CharField(read_only=True, source="get_logo_url", help_text="应用的Logo地址")

    class Meta:
        model = Application
        fields = ["id", "type", "code", "name", "logo_url"]


class MarketAppMinimalSLZ(serializers.Serializer):
    name = serializers.CharField()


class ApplicationWithMarketMinimalSLZ(serializers.Serializer):
    application = ApplicationMinimalSLZ(read_only=True)
    product = MarketAppMinimalSLZ(read_only=True)


class ApplicationMarkedSLZ(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="api.user.mark.applications.detail", lookup_field="code", help_text="单条记录访问链接"
    )

    application_code = serializers.ReadOnlyField(source="application.code", help_text="应用编码")
    application_name = serializers.ReadOnlyField(source="application.code", help_text="应用名称")
    application = ApplicationField(
        slug_field="code",
        many=False,
        allow_null=True,
        help_text="应用id",
    )

    def validate(self, attrs):
        if (
            self.context["request"].method in ["POST"]
            and self.Meta.model.objects.filter(
                owner=self.context["request"].user.pk, application__code=attrs["application"].code
            ).exists()
        ):
            raise ValidationError(_("已经标记该应用"))
        return attrs

    class Meta:
        model = UserMarkedApplication
        fields = ["application_code", "application_name", "application", "url"]

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user.pk
        validated_data["tenant_id"] = validated_data["application"].tenant_id
        return super(ApplicationMarkedSLZ, self).create(validated_data)

    def __repr__(self):
        return self.application_name


class ModuleEnvSLZ(serializers.Serializer):
    module = MinimalModuleSLZ()
    environment = serializers.CharField()


class ApplicationFeatureFlagSLZ(serializers.Serializer):
    name = serializers.CharField()
    effect = serializers.BooleanField()


class ProtectionStatusSLZ(serializers.Serializer):
    """Serialize app resource protection status"""

    activated = serializers.BooleanField(help_text="是否激活保护")
    reason = serializers.CharField(help_text="具体原因")


class ApplicationLogoSLZ(serializers.ModelSerializer):
    """Serializer for representing and modifying Logo"""

    logo = serializers.ImageField(write_only=True)
    logo_url = serializers.ReadOnlyField(source="get_logo_url", help_text="应用 Logo 访问地址")
    code = serializers.ReadOnlyField(help_text="应用 Code")

    class Meta:
        model = Application
        fields = ["logo", "logo_url", "code"]

    @atomic
    def update(self, instance: Application, validated_data: Dict) -> Dict:
        result = super().update(instance, validated_data)
        # Send signal to trigger extra processes for logo
        application_logo_updated.send(sender=instance, application=instance)
        return result


class ApplicationMembersInfoSLZ(serializers.ModelSerializer):
    name = TranslatedCharField()
    administrators = serializers.SerializerMethodField(help_text="应用管理人员名单")
    devopses = serializers.SerializerMethodField(help_text="应用运营人员名单")
    developers = serializers.SerializerMethodField(help_text="应用开发人员名单")
    last_operator = serializers.SerializerMethodField(help_text="最近操作人员")

    def get_administrators(self, application: Application):
        return application.get_administrators()

    def get_devopses(self, application: Application):
        return application.get_devopses()

    def get_developers(self, application: Application):
        return application.get_developers()

    def get_last_operator(self, application: Application):
        return get_last_operator(application)

    class Meta:
        model = Application
        fields = ["id", "code", "name", "administrators", "devopses", "developers", "last_operator"]


class ApplicationDeploymentModuleOrderSLZ(serializers.Serializer):
    module_name = serializers.CharField(max_length=20, required=True, help_text="模块名称")
    order = serializers.IntegerField(required=True, help_text="模块顺序")


class ApplicationDeploymentModuleOrderReqSLZ(serializers.Serializer):
    module_orders = ApplicationDeploymentModuleOrderSLZ(many=True, required=True)

    def validate(self, data):
        code = self.context.get("code")
        if not code:
            raise ValidationError("Cannot get app code")

        all_module_names = set(Module.objects.filter(application__code=code).values_list("name", flat=True))

        module_names = set()
        orders = set()

        for module in data["module_orders"]:
            module_name = module["module_name"]
            order = module["order"]

            # Check for duplicate module_name
            if module_name in module_names:
                raise ValidationError(f"Duplicate module_name: {module_name}.")
            # Check for duplicate order
            if order in orders:
                raise ValidationError(f"Duplicate order: {order}.")

            # check if the module_name is a module of the app
            if module_name not in all_module_names:
                raise ValidationError(f"No module named as {module_name}.")

            module_names.add(module_name)
            orders.add(order)

        # Check if all modules for the app code have set an order
        missing_orders = all_module_names - module_names
        if missing_orders:
            raise ValidationError(f"Modules missing an order: {', '.join(missing_orders)}.")

        return data
