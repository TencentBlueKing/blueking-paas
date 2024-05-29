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
from typing import Dict, Optional, Type

import arrow
import cattr
import semver
from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.bk_plugins.pluginscenter.constants import (
    LogTimeChoices,
    PluginReleaseStatus,
    PluginReleaseStrategy,
    PluginReleaseType,
    PluginReleaseVersionRule,
    PluginRole,
    SemverAutomaticType,
)
from paasng.bk_plugins.pluginscenter.definitions import FieldSchema, PluginConfigColumnDefinition
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.iam_adaptor.management import shim as iam_api
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ItsmTicketStatus
from paasng.bk_plugins.pluginscenter.models import (
    OperationRecord,
    PluginBasicInfoDefinition,
    PluginDefinition,
    PluginInstance,
    PluginMarketInfo,
    PluginRelease,
    PluginReleaseStage,
    PluginVisibleRange,
)
from paasng.infras.accounts.utils import get_user_avatar
from paasng.utils.es_log.time_range import SmartTimeRange
from paasng.utils.i18n.serializers import I18NExtend, TranslatedCharField, i18n, to_translated_field

REVISION_POLICIES = {
    "disallow_released_source_version": {"error": error_codes.CANNOT_RELEASE_DUPLICATE_SOURCE_VERSION, "filter": {}},
    "disallow_releasing_source_version": {
        "error": error_codes.CANNOT_RELEASE_RELEASING_SOURCE_VERSION,
        "filter": {"status__in": PluginReleaseStatus.running_status()},
    },
}


class PluginUniqueValidator:
    requires_context = True

    def __init__(self, id_field_label: str, name_field_label: str):
        self.id_field_label = id_field_label
        self.name_field_label = name_field_label
        self.queryset = PluginInstance.objects.all()

    def __call__(self, attrs, serializer):
        # Determine the existing instance, if this is an update operation.
        if "pd" not in serializer.context:
            raise ValidationError(_("context `pd` is required"), code="required")
        pd = serializer.context["pd"]

        queryset = self.queryset
        queryset = self.exclude_current_instance(attrs, queryset, serializer.instance)
        self.validate_queryset(queryset, pd_id=pd.identifier, attrs=attrs)

    def validate_queryset(self, queryset, pd_id, attrs: Dict):
        """validate the queryset to all instances matching the given attributes."""
        queryset = queryset.filter(pd__identifier=pd_id)
        fields = [
            {"name": "id", "label": self.id_field_label},
            *[
                {
                    "name": to_translated_field("name", language_code=lang[0]),
                    "label": self.name_field_label,
                }
                for lang in settings.LANGUAGES
            ],
        ]
        checked = False
        for field in fields:
            field_name = field["name"]
            field_label = field["label"]
            if field_name in attrs:
                value = attrs[field_name]
                if queryset.filter(**{field_name: value}).exists():
                    raise ValidationError(_("{} 为 {} 的插件已存在").format(field_label, value), code="unique")
                checked = True
        if not checked:
            raise ValidationError(_("attrs `{}` is required").format([f["name"] for f in fields]), code="required")

    def exclude_current_instance(self, attrs, queryset, instance):
        """
        If an instance is being updated, then do not include
        that instance itself as a uniqueness conflict.
        """
        if instance is not None:
            return queryset.exclude(pk=instance.pk)
        return queryset


class ItsmDetailSLZ(serializers.Serializer):
    ticket_url = serializers.CharField(default=None)
    sn = serializers.CharField(help_text="ITSM 单据单号")
    fields = serializers.ListField(child=serializers.DictField())


class PluginRoleSLZ(serializers.Serializer):
    name = serializers.CharField(read_only=True, help_text="角色名称")
    id = serializers.ChoiceField(help_text="角色ID", choices=PluginRole.get_choices())


class PluginMemberSLZ(serializers.Serializer):
    username = serializers.CharField(help_text="用户名")
    role = PluginRoleSLZ(help_text="角色")
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        return get_user_avatar(obj.username)


class ApprovalConfigSLZ(serializers.Serializer):
    enabled = serializers.BooleanField(default=False)
    tips = serializers.CharField(default=None)
    docs = serializers.CharField(default=None)


class PluginDefinitionSLZ(serializers.ModelSerializer):
    id = serializers.CharField(source="identifier")
    name = TranslatedCharField()
    description = TranslatedCharField()
    approval_config = ApprovalConfigSLZ()

    class Meta:
        model = PluginDefinition
        exclude = (
            "uuid",
            "identifier",
            "created",
            "updated",
            "release_revision",
            "release_stages",
            "test_release_revision",
            "test_release_stages",
            "log_config",
        )


class PluginBasicInfoDefinitionSLZ(serializers.ModelSerializer):
    description = TranslatedCharField()
    publisher_description = TranslatedCharField()

    class Meta:
        model = PluginBasicInfoDefinition
        exclude = (
            "id",
            "pd",
            "created",
            "updated",
            "id_schema",
            "name_schema",
            "init_templates",
            "release_method",
            "repository_group",
            "api",
            "sync_members",
            "extra_fields",
            "extra_fields_en",
            "extra_fields_order",
            "overview_page",
        )


class PluginDefinitionBasicSLZ(serializers.ModelSerializer):
    id = serializers.CharField(source="identifier")
    name = TranslatedCharField()

    class Meta:
        model = PluginDefinition
        fields = ("id", "name")


class PlainReleaseStageSLZ(serializers.Serializer):
    id = serializers.CharField(help_text="阶段id")
    name = serializers.CharField(help_text="阶段名称")


class PluginReleaseStageSLZ(serializers.ModelSerializer):
    itsm_detail = ItsmDetailSLZ()
    has_post_command = serializers.ReadOnlyField()

    class Meta:
        model = PluginReleaseStage
        exclude = ("id", "release", "created", "updated", "next_stage")


class PlainPluginReleaseVersionSLZ(serializers.Serializer):
    version = serializers.CharField(help_text="版本号")
    source_version_type = serializers.CharField(help_text="代码版本类型(branch/tag)")
    source_version_name = serializers.CharField(help_text="代码分支名/tag名")
    source_hash = serializers.CharField(help_text="代码提交哈希")
    creator = serializers.CharField(help_text="部署人")
    created = serializers.DateTimeField(help_text="部署时间")


class PluginReleaseVersionSLZ(serializers.ModelSerializer):
    current_stage = PluginReleaseStageSLZ()
    all_stages = PlainReleaseStageSLZ(many=True, source="stages_shortcut")
    complete_time = serializers.ReadOnlyField()
    report_url = serializers.SerializerMethodField(read_only=True)

    def get_report_url(self, instance) -> Optional[str]:
        release_definition = instance.plugin.pd.get_release_revision_by_type(instance.type)
        if release_definition.reportFromat:
            return release_definition.reportFromat.format(plugin_id=instance.plugin.id, version_id=instance.version)
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["creator"]:
            user = get_user_by_user_id(data["creator"])
            data["creator"] = user.username
        return data

    class Meta:
        model = PluginRelease
        exclude = ("plugin", "stages_shortcut")


class overviewPageSLZ(serializers.Serializer):
    top_url = serializers.CharField(default=None, source="topUrl")
    bottom_url = serializers.CharField(default=None, source="bottomUrl")


class PluginInstanceSLZ(serializers.ModelSerializer):
    pd_id = serializers.CharField(source="pd.identifier", help_text="插件类型标识")
    pd_name = serializers.CharField(source="pd.name", help_text="插件类型名称")
    pd_administrator = serializers.JSONField(source="pd.administrator", help_text="插件管理员")
    ongoing_release = PluginReleaseVersionSLZ(
        source="all_versions.get_ongoing_release", help_text="当前正在发布的版本", allow_null=True
    )
    latest_release = PluginReleaseVersionSLZ(
        source="all_versions.get_latest_release", help_text="最新的版本", allow_null=True
    )
    logo = serializers.CharField(source="get_logo_url", help_text="插件logo", allow_null=True)
    itsm_detail = ItsmDetailSLZ()
    role = PluginRoleSLZ(required=False)
    overview_page = overviewPageSLZ(source="get_overview_page")
    can_reactivate = serializers.ReadOnlyField()
    has_test_version = serializers.ReadOnlyField()

    class Meta:
        model = PluginInstance
        exclude = ("pd", "uuid")


class PluginInstanceDetailSLZ(PluginInstanceSLZ):
    def to_representation(self, instance):
        # 注入当前用户的角色信息
        if (request := self.context.get("request")) and request.user.is_authenticated:
            setattr(instance, "role", iam_api.fetch_user_main_role(instance, username=request.user.username))
        return super().to_representation(instance)


class PluginInstanceLogoSLZ(serializers.ModelSerializer):
    logo = serializers.ImageField(write_only=True)

    class Meta:
        model = PluginInstance
        fields = ["logo"]


class PluginMarketInfoSLZ(serializers.ModelSerializer):
    introduction = TranslatedCharField()
    description = TranslatedCharField()

    class Meta:
        model = PluginMarketInfo
        fields = ("category", "description", "introduction", "contact", "extra_fields")


class TemplateChoiceField(serializers.ChoiceField):
    """A ChoiceField for choosing template, accept a string of template name and return the template definition instead

    usage:
        TemplateChoiceField(
            choices=[(template.id, template) for template in pd.basic_info_definition.init_templates]
        )
    where:
        pd: PluginDefinition
    """

    def to_internal_value(self, data):
        return self.choices[super().to_internal_value(data)]


def _get_init_kwargs(field_schema: FieldSchema) -> dict:
    init_kwargs = {
        "label": field_schema.title,
        "help_text": field_schema.description,
        "max_length": field_schema.maxlength,
    }
    if (not field_schema.uiRules) or ("required" not in field_schema.uiRules):
        init_kwargs["allow_null"] = True
        init_kwargs["allow_blank"] = True
    if field_schema.default:
        init_kwargs["default"] = field_schema.default
    return init_kwargs


def make_string_field(field_schema: FieldSchema) -> serializers.Field:
    """Generate a Field for verifying a string according to the given field_schema"""
    init_kwargs = _get_init_kwargs(field_schema)
    if field_schema.pattern:
        return serializers.RegexField(regex=field_schema.pattern, **init_kwargs)
    return serializers.CharField(**init_kwargs)


def make_array_field(field_schema: FieldSchema) -> serializers.Field:
    """Generate a Field for verifying a array according to the given field_schema"""
    init_kwargs = _get_init_kwargs(field_schema)
    # 如果没有定义 items，则默认为：List[str]
    if not field_schema.items:
        return serializers.ListField(child=serializers.CharField(**init_kwargs))
    child_field_schema = cattr.structure(field_schema.items, FieldSchema)
    child_field = make_json_schema_field(child_field_schema)
    return serializers.ListField(child=child_field)


def make_bool_field(field_schema: FieldSchema) -> serializers.Field:
    """Generate a Field for verifying a bool according to the given field_schema"""
    return serializers.BooleanField(default=field_schema.default)


def make_json_schema_field(field_schema: FieldSchema) -> serializers.Field:
    """Generate fields for validating data according to the given field_schema"""
    type_ = field_schema.type
    if type_ == "array":
        return make_array_field(field_schema)
    elif type_ == "string":
        return make_string_field(field_schema)
    elif type_ == "boolean":
        return make_bool_field(field_schema)
    raise NotImplementedError(f"NotImplemented field type: {type_} for plugin's extraFields")


def make_extra_fields_slz(extra_fields: Dict[str, FieldSchema]) -> Type[serializers.Serializer]:
    """generate a Serializer for verifying the fields of ExtraFields"""
    return type(
        "ExtraFieldSLZ",
        (serializers.Serializer,),
        {key: make_json_schema_field(field) for key, field in extra_fields.items()},
    )


def make_plugin_slz_class(pd: PluginDefinition, creation: bool = False) -> Type[serializers.Serializer]:
    """generate a SLZ for verifying the creation/update of "Plugin" according to the PluginDefinition definition"""
    fields = {
        "name": I18NExtend(make_json_schema_field(pd.basic_info_definition.name_schema)),
        "extra_fields": make_extra_fields_slz(pd.basic_info_definition.extra_fields)(default=dict),
        "Meta": type(
            "Meta",
            (),
            {
                "validators": [
                    PluginUniqueValidator(
                        id_field_label=pd.basic_info_definition.id_schema.title,
                        name_field_label=pd.basic_info_definition.name_schema.title,
                    )
                ]
            },
        ),
    }
    if creation:
        fields["id"] = make_json_schema_field(pd.basic_info_definition.id_schema)
        fields["template"] = TemplateChoiceField(
            choices=[(template.id, template) for template in pd.basic_info_definition.init_templates]
        )
    return i18n(type("DynamicPluginSerializer", (serializers.Serializer,), fields))


def make_extra_fields_class(pd: PluginDefinition) -> Type[serializers.Serializer]:
    fields = {
        "extra_fields": make_extra_fields_slz(pd.basic_info_definition.extra_fields)(default=dict),
    }
    return i18n(type("DynamicPluginMarketInfoSerializer", (serializers.Serializer,), fields))


class StubCreatePluginSLZ(serializers.Serializer):
    """A stub Serializer for create `Plugin`, just be used to generate docs

    Please see the specific implementation at `make_plugin_slz_class`
    """

    id = serializers.CharField(help_text="插件id")
    name = serializers.CharField(help_text="插件名称")
    template = serializers.CharField(help_text="模板id")
    extra_fields = serializers.DictField(help_text="额外字段")


class StubUpdatePluginSLZ(serializers.Serializer):
    """A stub Serializer for update `Plugin`, just be used to generate docs

    Please see the specific implementation at `make_plugin_slz_class`
    """

    name = serializers.CharField(help_text="插件名称")
    extra_fields = serializers.DictField(help_text="额外字段")


class ReleaseStrategySLZ(serializers.Serializer):
    strategy = serializers.ChoiceField(choices=PluginReleaseStrategy.get_choices(), help_text="发布策略")
    bkci_project = serializers.ListField(required=False, allow_null=True, help_text="蓝盾项目ID")
    organization = serializers.ListField(required=False, allow_null=True, help_text="组织架构")


def make_release_validator(  # noqa: C901
    plugin: PluginInstance, version_rule: PluginReleaseVersionRule, release_type: str, revision_policy: Optional[str]
):
    """make a validator to validate ReleaseVersion object"""

    def validate_semver(version: str, previous_version_str: Optional[str], semver_type: SemverAutomaticType):
        try:
            parsed_version = semver.VersionInfo.parse(version)
            previous_version = semver.VersionInfo.parse(previous_version_str or "0.0.0")
        except ValueError as e:
            raise ValidationError(str(e))
        if semver_type == SemverAutomaticType.MAJOR:
            computational_revision = previous_version.bump_major()
        elif semver_type == SemverAutomaticType.MINOR:
            computational_revision = previous_version.bump_minor()
        else:
            computational_revision = previous_version.bump_patch()
        if computational_revision != parsed_version:
            raise ValidationError(
                {
                    "revision": _("版本号不符合，下一个 {label} 版本是 {revision}").format(
                        label=SemverAutomaticType.get_choice_label(semver_type), revision=computational_revision
                    )
                }
            )
        return True

    def validate_release_policy(
        plugin: PluginInstance, release_type: str, revision_policy: str, source_version_name: str
    ):
        """Plugin version release rules, e.g., cannot release already published versions."""
        policy = REVISION_POLICIES.get(revision_policy)
        if policy:
            source_version_exists = PluginRelease.objects.filter(
                plugin=plugin, source_version_name=source_version_name, type=release_type, **policy["filter"]
            ).exists()
            if source_version_exists:
                raise policy["error"]  # type: ignore[misc]
        return True

    def validator(self, attrs: Dict):
        version = attrs["version"]
        if version_rule == PluginReleaseVersionRule.AUTOMATIC:
            validate_semver(version, self.context["previous_version"], SemverAutomaticType(attrs["semver_type"]))
        elif version_rule == PluginReleaseVersionRule.REVISION:
            if version != attrs["source_version_name"]:
                raise ValidationError(_("版本号必须与代码分支一致"))
        elif version_rule == PluginReleaseVersionRule.COMMIT_HASH:  # noqa: SIM102
            if version != self.context["source_hash"]:
                raise ValidationError(_("版本号必须与提交哈希一致"))
        elif version_rule == PluginReleaseVersionRule.BRANCH_TIMESTAMP:  # noqa: SIM102
            if not version.startswith(attrs["source_version_name"]):
                raise ValidationError(_("版本号必须以代码分支开头"))

        if revision_policy:
            validate_release_policy(plugin, release_type, revision_policy, attrs["source_version_name"])
        return attrs

    return validator


def make_create_release_version_slz_class(plugin: PluginInstance, release_type: str) -> Type[serializers.Serializer]:
    """Generate a Serializer for verifying the creation of "Prod Release" according to the PluginDefinition definition"""
    release_definition = plugin.pd.get_release_revision_by_type(release_type)
    if release_definition.revisionPattern:
        source_version_field = serializers.RegexField(release_definition.revisionPattern, help_text="分支名/tag名")
    else:
        source_version_field = serializers.CharField(help_text="分支名/tag名")

    fields = {
        "type": serializers.ChoiceField(
            help_text="版本类型", choices=PluginReleaseType.get_choices(), default=release_type
        ),
        "source_version_type": serializers.CharField(help_text="代码版本类型(branch/tag)"),
        "source_version_name": source_version_field,
        "version": serializers.CharField(help_text="版本号"),
        "comment": serializers.CharField(help_text="版本日志"),
        "extra_fields": make_extra_fields_slz(release_definition.extraFields)(default=dict),
        "release_strategy": ReleaseStrategySLZ(required=False, allow_null=True, help_text="发布策略"),
    }
    if release_definition.versionNo == PluginReleaseVersionRule.AUTOMATIC:
        fields["semver_type"] = serializers.ChoiceField(
            choices=SemverAutomaticType.get_choices(), help_text="版本类型"
        )

    return type(
        "DynamicPluginReleaseSerializer",
        (serializers.Serializer,),
        {
            **fields,
            # implement `validate` method of serializers.Serializer
            "validate": make_release_validator(
                plugin,
                PluginReleaseVersionRule(release_definition.versionNo),
                release_type,
                release_definition.revisionPolicy,
            ),
        },
    )


class StubCreatePluginReleaseVersionSLZ(serializers.Serializer):
    """A stub Serializer for create `Release`, just be used to generate docs

    Please see the specific implementation at `make_create_release_version_slz_class`
    """

    source_version_type = serializers.CharField(help_text="代码版本类型(branch/tag)")
    source_version_name = serializers.CharField(help_text="分支名/tag名")
    version = serializers.CharField(help_text="版本号")
    comment = serializers.CharField(help_text="版本日志")
    extra_fields = serializers.DictField(help_text="额外字段")
    semver_type = serializers.CharField(help_text="版本类型(仅 versionNo=automatic 需要传递)", allow_null=True)


def make_market_info_slz_class(pd: PluginDefinition) -> Type[serializers.Serializer]:
    """Generate a SLZ for verifying the creation/update of "Market" according to the PluginDefinition definition"""
    fields = {
        "category": serializers.CharField(help_text="市场类别"),
        "introduction": I18NExtend(serializers.CharField(help_text="简介")),
        "description": I18NExtend(serializers.CharField(help_text="详细描述", allow_null=True, allow_blank=True)),
        "contact": serializers.CharField(help_text="联系人, 以;分割"),
        "extra_fields": make_extra_fields_slz(pd.market_info_definition.extra_fields)(default=dict),
    }
    return i18n(type("DynamicPluginMarketInfoSerializer", (serializers.Serializer,), fields))


class StubUpsertMarketInfoSLZ(serializers.Serializer):
    """A stub Serializer for creation/update  `Market`, just be used to generate docs

    Please see the specific implementation at `make_market_info_slz_class`
    """

    category = serializers.CharField(help_text="市场类别")
    introduction = TranslatedCharField(help_text="简介")
    description = TranslatedCharField(help_text="详细描述", allow_blank=True, allow_null=True)
    contact = serializers.CharField(help_text="联系人, 以;分割")
    extra_fields = serializers.DictField(help_text="额外字段")


class PluginLogQueryParamsSLZ(serializers.Serializer):
    """查询插件日志 query 参数"""

    time_range = serializers.ChoiceField(choices=LogTimeChoices.get_choices(), required=True)
    start_time = serializers.DateTimeField(help_text="format %Y-%m-%d %H:%M:%S", allow_null=True, required=False)
    end_time = serializers.DateTimeField(help_text="format %Y-%m-%d %H:%M:%S", allow_null=True, required=False)
    offset = serializers.IntegerField(default=0, help_text="偏移量=页码*每页数量")
    limit = serializers.IntegerField(default=100, help_text="每页数量")

    def validate(self, attrs):
        try:
            time_range = SmartTimeRange(
                time_range=attrs["time_range"],
                start_time=attrs.get("start_time"),
                end_time=attrs.get("end_time"),
            )
        except ValueError as e:
            raise ValidationError({"time_range": str(e)})
        attrs["smart_time_range"] = time_range
        return attrs


class PluginLogQueryDSLSLZ(serializers.Serializer):
    """查询插件日志的 DSL 参数"""

    query_string = serializers.CharField(help_text="查询语句", default="", allow_blank=True)
    terms = serializers.DictField(help_text="多值精准匹配", default=dict)
    exclude = serializers.DictField(help_text="terms 取反", default=dict)


class PluginLogQueryBodySLZ(serializers.Serializer):
    """查询插件标准输出的 body 参数"""

    query = PluginLogQueryDSLSLZ()


class StandardOutputLogLineSLZ(serializers.Serializer):
    """标准输出日志(每行)"""

    timestamp = serializers.IntegerField(help_text="时间戳")
    message = serializers.CharField(help_text="日志内容")


class StandardOutputLogsSLZ(serializers.Serializer):
    """标准输出日志"""

    logs = StandardOutputLogLineSLZ(many=True)
    total = serializers.IntegerField(help_text="总日志量, 用于计算页数")
    dsl = serializers.CharField(help_text="日志查询语句")


class StructureLogLineSLZ(serializers.Serializer):
    """结构化日志(每行)"""

    timestamp = serializers.IntegerField(help_text="时间戳")
    message = serializers.CharField(help_text="日志内容")
    raw = serializers.DictField(help_text="日志详情")


class StructureLogsSLZ(serializers.Serializer):
    """结构化日志"""

    logs = StructureLogLineSLZ(many=True)
    total = serializers.IntegerField(help_text="总日志量, 用于计算页数")
    dsl = serializers.CharField(help_text="日志查询语句")


class IngressLogLineSLZ(serializers.Serializer):
    """Ingress 访问日志(每行)"""

    timestamp = serializers.IntegerField(help_text="时间戳")
    message = serializers.CharField(help_text="日志内容")
    method = serializers.CharField(help_text="请求方法", default=None)
    path = serializers.CharField(help_text="请求路径", default=None)
    status_code = serializers.IntegerField(help_text="状态码", default=None)
    response_time = serializers.FloatField(help_text="返回耗时", default=None)
    client_ip = serializers.CharField(help_text="客户端IP", default=None)
    bytes_sent = serializers.IntegerField(help_text="返回体大小", default=None)
    user_agent = serializers.CharField(help_text="UserAgent", default=None)
    http_version = serializers.CharField(help_text="http 版本号", default=None)


class IngressLogSLZ(serializers.Serializer):
    """Ingress 访问日志"""

    logs = IngressLogLineSLZ(many=True)
    total = serializers.IntegerField(help_text="总日志量, 用于计算页数")
    dsl = serializers.CharField(help_text="日志查询语句")


class DateHistogramSLZ(serializers.Serializer):
    """插件日志基于时间分布的直方图"""

    series = serializers.ListField(child=serializers.IntegerField(), help_text="按时间排序的值(文档数)")
    timestamps = serializers.ListField(
        child=serializers.IntegerField(), help_text="Series 中对应位置记录的时间点的时间戳"
    )
    dsl = serializers.CharField(help_text="日志查询语句")


class LogFieldFilterSLZ(serializers.Serializer):
    """日志可选字段"""

    name = serializers.CharField(help_text="展示名称")
    key = serializers.CharField(help_text="传递给参数中的key")
    options = serializers.ListField(help_text="该字段的选项和分布频率")
    total = serializers.IntegerField(help_text="该字段在日志(top200)出现的频次")


class ItsmTicketInfoSlz(serializers.Serializer):
    """itsm 单据状态"""

    ticket_url = serializers.CharField(help_text="单据详情链接")
    current_status = serializers.CharField(help_text="单据状态")
    current_status_display = serializers.CharField(help_text="单据状态显示文案")
    can_withdraw = serializers.BooleanField(help_text="是否可撤销单据")
    fields = serializers.ListField(help_text="提单信息")


class ItsmApprovalSLZ(serializers.Serializer):
    """Itsm 回调数据格式"""

    sn = serializers.CharField(label="申请的单据号")
    current_status = serializers.ChoiceField(label="单据当前状态", choices=ItsmTicketStatus.get_choices())
    approve_result = serializers.BooleanField(label="审批结果")
    token = serializers.CharField(label="回调token", help_text="可用于验证请求是否来自于 ITSM")


class PluginConfigColumnSLZ(serializers.Serializer):
    """插件「配置管理」表单-列定义"""

    name = serializers.CharField(help_text="该字段对应的变量名")
    title = serializers.CharField(help_text="字段的标题")
    description = serializers.CharField(help_text="字段描述(placeholder)")
    pattern = serializers.CharField(required=False, help_text="校验字段的正则表达式")
    options = serializers.DictField(required=False, help_text="字段的选项, 格式是 {'选项展示名称': '选项值'}")


class PluginConfigSchemaSLZ(serializers.Serializer):
    """插件「配置管理」表单范式"""

    title = TranslatedCharField(help_text="「配置管理」的标题")
    description = TranslatedCharField(help_text="「配置管理」的描述")
    docs = serializers.CharField(default=None)
    columns = PluginConfigColumnSLZ(many=True)


def make_config_column_field(column_definition: PluginConfigColumnDefinition) -> serializers.Field:
    """Generate a Field for verifying a string according to the given column_definition"""
    init_kwargs = {
        "label": column_definition.title,
        "help_text": column_definition.description,
    }
    if column_definition.pattern:
        return serializers.RegexField(regex=column_definition.pattern, **init_kwargs)
    return serializers.CharField(**init_kwargs)


def make_config_slz_class(pd: PluginDefinition) -> Type[serializers.Serializer]:
    """generate a SLZ for verifying the creation/update of "Plugin Config"
    according to the PluginConfigDefinition definition"""
    fields = {}
    # 部分插件未定义配置管理
    if hasattr(pd, "config_definition"):
        config_definition = pd.config_definition
        fields = {
            column_definition.name: make_config_column_field(column_definition)
            for column_definition in config_definition.columns
        }
        fields["__id__"] = serializers.CharField(help_text="配置项id", required=False)
    return type("DynamicPluginConfigSerializer", (serializers.Serializer,), fields)


class StubConfigSLZ(serializers.Serializer):
    """A stub Serializer for creation/update  `Configuration`, just be used to generate docs

    Please see the specific implementation at `make_config_slz_class`
    """

    __id__ = serializers.CharField(help_text="配置项id", source="unique_key")


class OperationRecordSLZ(serializers.ModelSerializer):
    display_text = serializers.CharField(source="get_display_text", read_only=True)

    class Meta:
        model = OperationRecord
        fields = "__all__"


class CodeCommitSearchSLZ(serializers.Serializer):
    """代码提交统计搜索条件"""

    begin_time = serializers.DateTimeField(help_text="format %Y-%m-%d %H:%M:%S", required=True)
    end_time = serializers.DateTimeField(help_text="format %Y-%m-%d %H:%M:%S", required=True)

    def to_internal_value(self, instance):
        data = super().to_internal_value(instance)

        # 将时间转换为代码仓库指定的格式  YYYY-MM-DDTHH:mm:ssZ
        data["begin_time"] = arrow.get(data["begin_time"]).format("YYYY-MM-DDTHH:mm:ssZ")
        data["end_time"] = arrow.get(data["end_time"]).format("YYYY-MM-DDTHH:mm:ssZ")
        return data


class PluginReleaseFilterSLZ(serializers.Serializer):
    status = serializers.ListField(required=False)
    type = serializers.ChoiceField(choices=PluginReleaseType.get_choices(), default=PluginReleaseType.PROD)
    creator = serializers.CharField(required=False)

    def validate(self, attrs):
        if "creator" in attrs:
            attrs["creator"] = user_id_encoder.encode(settings.USER_TYPE, attrs["creator"])
        return attrs


class PluginListFilterSlZ(serializers.Serializer):
    status = serializers.ListField(required=False)
    language = serializers.ListField(required=False)
    pd__identifier = serializers.ListField(required=False)


class CodeCheckInfoSLZ(serializers.Serializer):
    """蓝盾 API 返回的代码检查结果的数据格式，保留驼峰格式"""

    resolvedDefectNum = serializers.FloatField(help_text="已解决缺陷数", required=False)
    repoCodeccAvgScore = serializers.IntegerField(help_text="代码质量", required=False)


class QualityInfoSLZ(serializers.Serializer):
    """蓝盾 API 返回的代码质量的数据格式，保留驼峰格式"""

    qualityInterceptionRate = serializers.FloatField(help_text="质量红线拦截率", required=False)
    interceptionCount = serializers.IntegerField(help_text="拦截次数", required=False)
    totalExecuteCount = serializers.IntegerField(help_text="运行总次数", required=False)


class MetricsSummarySLZ(serializers.Serializer):
    """蓝盾 API 返回的代码仓库概览信息的数据格式，保留驼峰格式"""

    codeCheckInfo = CodeCheckInfoSLZ(required=False)
    qualityInfo = QualityInfoSLZ(required=False)


class PluginReleaseTypeSLZ(serializers.Serializer):
    """插件发布类型"""

    type = serializers.ChoiceField(choices=PluginReleaseType.get_choices(), default=PluginReleaseType.PROD)


class PluginStageStatusSLZ(serializers.Serializer):
    """插件状态"""

    status = serializers.ChoiceField(choices=PluginReleaseStatus.get_choices())
    message = serializers.CharField(default="")


class PluginPublisher(serializers.Serializer):
    """插件发布者"""

    publisher = serializers.CharField(help_text="插件发布者")


class PluginVisibleRangeSLZ(serializers.ModelSerializer):
    itsm_detail = ItsmDetailSLZ()

    class Meta:
        model = PluginVisibleRange
        fields = "__all__"


class PluginVisibleRangeUpdateSLZ(serializers.Serializer):
    bkci_project = serializers.ListField(child=serializers.CharField(), help_text="格式：['1111', '222222']")
    organization = serializers.ListField(child=serializers.DictField())
