"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import Dict, Optional, Type

import semver
from bkpaas_auth import get_user_by_user_id
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.accounts.utils import get_user_avatar
from paasng.pluginscenter.constants import LogTimeChoices, PluginReleaseVersionRule, PluginRole, SemverAutomaticType
from paasng.pluginscenter.definitions import FieldSchema, PluginConfigColumnDefinition
from paasng.pluginscenter.itsm_adaptor.constants import ItsmTicketStatus
from paasng.pluginscenter.models import (
    PluginDefinition,
    PluginInstance,
    PluginMarketInfo,
    PluginRelease,
    PluginReleaseStage,
)
from paasng.pluginscenter.thirdparty.log import SmartTimeRange
from paasng.utils.i18n.serializers import I18NExtend, TranslatedCharField, i18n


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
        exclude = ("uuid", "identifier", "created", "updated", "release_revision", "release_stages", "log_config")


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data['creator']:
            user = get_user_by_user_id(data['creator'])
            data['creator'] = user.username
        return data

    class Meta:
        model = PluginRelease
        exclude = ("plugin", "stages_shortcut")


class ItsmDetailSLZ(serializers.Serializer):
    ticket_url = serializers.CharField(default=None)


class PluginInstanceSLZ(serializers.ModelSerializer):
    pd_id = serializers.CharField(source="pd.identifier", help_text="插件类型标识")
    pd_name = serializers.CharField(source="pd.name", help_text="插件类型名称")
    ongoing_release = PluginReleaseVersionSLZ(
        source="all_versions.get_ongoing_release", help_text="当前正在发布的版本", allow_null=True
    )
    logo = serializers.CharField(source="pd.logo", help_text="插件logo", allow_null=True)
    itsm_detail = ItsmDetailSLZ()

    class Meta:
        model = PluginInstance
        exclude = ("pd", "uuid")


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


def make_string_field(field_schema: FieldSchema) -> serializers.Field:
    """Generate a Field for verifying a string according to the given field_schema"""
    init_kwargs = {
        "label": field_schema.title,
        "help_text": field_schema.description,
    }
    if field_schema.default:
        init_kwargs["default"] = field_schema.default
    if field_schema.pattern:
        return serializers.RegexField(regex=field_schema.pattern, **init_kwargs)
    return serializers.CharField(**init_kwargs)


def make_extra_fields_slz(extra_fields: Dict[str, FieldSchema]) -> Type[serializers.Serializer]:
    """generate a Serializer for verifying the fields of ExtraFields"""
    return type(
        "ExtraFieldSLZ",
        (serializers.Serializer,),
        {key: make_string_field(field) for key, field in extra_fields.items()},
    )


def make_plugin_slz_class(pd: PluginDefinition, creation: bool = False) -> Type[serializers.Serializer]:
    """generate a SLZ for verifying the creation/update of "Plugin" according to the PluginDefinition definition"""
    fields = {
        "name": I18NExtend(make_string_field(pd.basic_info_definition.name_schema)),
        "extra_fields": make_extra_fields_slz(pd.basic_info_definition.extra_fields)(default=dict),
    }
    if creation:
        fields["id"] = make_string_field(pd.basic_info_definition.id_schema)
        fields["template"] = TemplateChoiceField(
            choices=[(template.id, template) for template in pd.basic_info_definition.init_templates]
        )
    return i18n(type("DynamicPluginSerializer", (serializers.Serializer,), fields))


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


def make_release_validator(version_rule: PluginReleaseVersionRule):
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

    def validator(self, attrs: Dict):
        version = attrs["version"]
        if version_rule == PluginReleaseVersionRule.AUTOMATIC:
            validate_semver(version, self.context["previous_version"], SemverAutomaticType(attrs["semver_type"]))
        elif version_rule == PluginReleaseVersionRule.REVISION:
            if version != attrs["source_version_name"]:
                raise ValidationError(_("版本号必须与代码分支一致"))
        elif version_rule == PluginReleaseVersionRule.COMMIT_HASH:
            if version != self.context["source_hash"]:
                raise ValidationError(_("版本号必须与提交哈希一致"))
        return attrs

    return validator


def make_create_release_version_slz_class(pd: PluginDefinition) -> Type[serializers.Serializer]:
    """Generate a Serializer for verifying the creation of "Release" according to the PluginDefinition definition"""
    if pd.release_revision.revisionPattern:
        source_version_field = serializers.RegexField(pd.release_revision.revisionPattern, help_text="分支名/tag名")
    else:
        source_version_field = serializers.CharField(help_text="分支名/tag名")

    fields = {
        "type": serializers.CharField(help_text="发布类型(正式/测试)", default="prod"),
        "source_version_type": serializers.CharField(help_text="代码版本类型(branch/tag)"),
        "source_version_name": source_version_field,
        "version": serializers.CharField(help_text="版本号"),
        "comment": serializers.CharField(help_text="版本日志"),
        "extra_fields": make_extra_fields_slz(pd.release_revision.extraFields)(default=dict),
    }
    if pd.release_revision.versionNo == PluginReleaseVersionRule.AUTOMATIC:
        fields["semver_type"] = serializers.ChoiceField(choices=SemverAutomaticType.get_choices(), help_text="版本类型")

    return type(
        "DynamicPluginReleaseSerializer",
        (serializers.Serializer,),
        {
            **fields,
            # implement `validate` method of serializers.Serializer
            "validate": make_release_validator(PluginReleaseVersionRule(pd.release_revision.versionNo)),
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


class PluginLogQueryBodySLZ(serializers.Serializer):
    """查询插件标准输出的 body 参数"""

    query_string = serializers.CharField(help_text="查询语句", default="")


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
    timestamps = serializers.ListField(child=serializers.IntegerField(), help_text="Series 中对应位置记录的时间点的时间戳")
    dsl = serializers.CharField(help_text="日志查询语句")


class PluginRoleSLZ(serializers.Serializer):
    name = serializers.CharField(read_only=True, help_text="角色名称")
    id = serializers.ChoiceField(help_text="角色ID", choices=PluginRole.get_choices())


class PluginMemberSLZ(serializers.Serializer):
    username = serializers.CharField(help_text="用户名")
    role = PluginRoleSLZ(help_text="角色")
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        return get_user_avatar(obj.username)


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
    config_definition = pd.config_definition
    fields = {
        column_definition.title: make_config_column_field(column_definition)
        for column_definition in config_definition.columns
    }
    fields["__id__"] = serializers.CharField(help_text="配置项id", source="unique_key")
    return type("DynamicPluginConfigSerializer", (serializers.Serializer,), fields)


class StubConfigSLZ(serializers.Serializer):
    """A stub Serializer for creation/update  `Configuration`, just be used to generate docs

    Please see the specific implementation at `make_config_slz_class`
    """

    __id__ = serializers.CharField(help_text="配置项id", source="unique_key")
