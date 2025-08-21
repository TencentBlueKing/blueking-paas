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
from datetime import datetime

import yaml
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.validators import UniqueTogetherValidator, qs_exists

from paas_wl.bk_app.applications.models import Build, BuildProcess
from paas_wl.bk_app.processes.kres_entities import Instance
from paas_wl.bk_app.processes.serializers import ProcessSpecSLZ
from paasng.accessories.publish.market.serializers import AvailableAddressSLZ
from paasng.misc.monitoring.metrics.constants import MetricsResourceType, MetricsSeriesType
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.constants import ImagePullPolicy
from paasng.platform.engine.constants import (
    ConfigVarEnvName,
    DeployConditions,
    JobStatus,
    MetricsType,
    ReplicasPolicy,
    RuntimeType,
)
from paasng.platform.engine.models import DeployPhaseTypes
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ENVIRONMENT_NAME_FOR_GLOBAL, ConfigVar
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.offline import OfflineOperation
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations
from paasng.platform.engine.phases_steps.display_blocks import DeployDisplayBlockRenderer
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.constants import VersionType
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.datetime import calculate_gap_seconds_interval, get_time_delta
from paasng.utils.error_codes import error_codes
from paasng.utils.masked_curlify import MASKED_CONTENT
from paasng.utils.models import OrderByField
from paasng.utils.serializers import UserField, field_env_var_key


class DeploymentAdvancedOptionsSLZ(serializers.Serializer):
    dev_hours_spent = serializers.FloatField(help_text="开发时长", required=False)
    image_pull_policy = serializers.ChoiceField(
        help_text="镜像拉取策略",
        required=False,
        choices=ImagePullPolicy.get_choices(),
        default=ImagePullPolicy.IF_NOT_PRESENT,
    )
    build_only = serializers.BooleanField(help_text="是否仅构建, 不发布", default=False)
    special_tag = serializers.CharField(
        help_text="指定构建的镜像 tag", required=False, allow_null=True, allow_blank=True
    )
    build_id = serializers.CharField(
        help_text="构建产物ID, 提供该ID时将跳过构建", required=False, allow_null=True, allow_blank=True
    )
    invoke_message = serializers.CharField(help_text="触发信息", required=False, allow_null=True, allow_blank=True)


class CreateDeploymentSLZ(serializers.Serializer):
    """创建部署"""

    version_type = serializers.ChoiceField(
        choices=VersionType.get_choices(),
        required=True,
        error_messages={"invalid_choice": f"Invalid choice. Valid choices are {VersionType.get_values()}"},
        help_text="版本类型, 如 branch/tag/trunk",
    )
    version_name = serializers.CharField(
        required=True, help_text="版本名称: 如 Tag Name/Branch Name/trunk/package_name"
    )
    revision = serializers.CharField(
        required=False,
        help_text="版本信息, 如 hash(git版本)/version(源码包); 如果根据 smart_revision 能查询到 revision, 则不使用该值",
    )

    advanced_options = DeploymentAdvancedOptionsSLZ(required=False, default={})

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if attrs["version_type"] == VersionType.IMAGE.value and not self._is_expected_revision(attrs.get("revision")):
            # 云原生应用选择已构建的镜像部署时, version_type 传入了 image
            # 这里加上强制校验, 保证 image 类型被正确使用(仅用于云原生应用选择已构建镜像时),
            # 否则会导致 Deployment.get_version_info 抛出 ValueError("unknown version info")
            raise ValidationError(_("version_type 为 image 时，revision 必须为 sha256 开头的镜像 digest"))
        return attrs

    def _is_expected_revision(self, revision):
        if not revision:
            return False

        # 由于镜像仓库的原因, 单一的 media_type 可能无法查到镜像的 digest(但镜像是存在的), 因此 revision 可能为 unknown
        if revision == "unknown":
            return True

        return self._is_image_digest(revision)

    @staticmethod
    def _is_image_digest(revision):
        return bool(re.match(r"^sha256:[0-9a-f]{64}$", revision))


class CreateDeploymentResponseSLZ(serializers.Serializer):
    deployment_id = serializers.CharField()
    stream_url = serializers.URLField()


class QueryDeploymentsSLZ(serializers.Serializer):
    environment = serializers.ChoiceField(choices=("stag", "prod"), required=False)
    operator = serializers.CharField(required=False)


class QueryOperationsSLZ(serializers.Serializer):
    environment = serializers.ChoiceField(choices=("stag", "prod"), required=False)
    operator = serializers.CharField(required=False)


class DeploymentSLZ(serializers.ModelSerializer):
    """This serializer is only for presentation purpose"""

    operator = UserField(read_only=True)
    start_time = serializers.DateTimeField(allow_null=True)
    complete_time = serializers.DateTimeField(allow_null=True)
    finished_status = serializers.CharField(allow_null=True)

    class Meta:
        model = Deployment
        fields = [
            "id",
            "status",
            "operator",
            "created",
            "start_time",
            "complete_time",
            "finished_status",
            "build_int_requested_at",
            "release_int_requested_at",
            "has_requested_int",
            "bkapp_revision_id",
        ]

    def get_repo_info(self, obj: Deployment) -> dict:
        """Get deployment's repo info as dict"""
        version_info = obj.get_version_info()
        revision = version_info.revision
        version_type = version_info.version_type
        version_name = version_info.version_name

        return {
            "source_type": obj.source_type,
            "type": version_type,
            "name": version_name,
            "url": obj.source_location,
            "revision": revision,
            "comment": obj.source_comment,
        }

    def to_representation(self, obj):
        """Format a obj to presentation"""
        result = super().to_representation(obj)
        result.update(
            # Add 'deployment_id' for backward compatibility
            deployment_id=obj.id,
            environment=obj.app_environment.environment,
            repo=self.get_repo_info(obj),
        )
        return result


class DeploymentErrorTipsSLZ(serializers.Serializer):
    matched_solutions_found = serializers.BooleanField(help_text="是否有匹配的 tips", allow_null=True)
    possible_reason = serializers.CharField(help_text="可能导致部署错误的原因")
    helpers = serializers.DictField()


class DeploymentResultSLZ(serializers.Serializer):
    status = serializers.ChoiceField(JobStatus.get_choices(), help_text="部署状态")
    logs = serializers.CharField(help_text="部署日志, 纯文本")
    error_detail = serializers.CharField(help_text="错误详情")
    error_tips = DeploymentErrorTipsSLZ()


class DeploymentResultQuerySLZ(serializers.Serializer):
    """部署结果查询参数序列化器"""

    include_ansi_codes = serializers.BooleanField(
        default=False,
        required=False,
        help_text="是否包含 ANSI 转义序列. true 保留终端颜色和格式控制字符, false 过滤这些字符",
    )


class BuildProcessSLZ(serializers.Serializer):
    """构建历史"""

    generation = serializers.IntegerField(help_text="执行ID")
    image_tag = serializers.SerializerMethodField(help_text="构建镜像")
    status = serializers.ChoiceField(choices=JobStatus.get_choices())
    invoke_message = serializers.CharField(help_text="触发信息")
    start_at = serializers.DateTimeField(help_text="开始时间", source="created")
    completed_at = serializers.DateTimeField(help_text="结束时间", allow_null=True)

    module = serializers.SerializerMethodField(help_text="所属模块")
    environment = serializers.SerializerMethodField(help_text="部署环境")
    deployment_id = serializers.SerializerMethodField(help_text="用于查询详情日志")
    build_id = serializers.CharField(source="build.uuid", allow_null=True)

    def get_deployment_id(self, bp: BuildProcess):
        # Note: 这里涉及多次数据库查询
        deployment = Deployment.objects.filter(build_process_id=bp.uuid).first()
        if deployment:
            return deployment.pk
        return None

    def get_module(self, bp: BuildProcess):
        # Note: 这里设计多次数据库查询
        module = Module.objects.filter(id=bp.module_id).first()
        if module:
            return module.name
        return None

    def get_environment(self, bp: BuildProcess):
        # Note: 这里设计多次数据库查询
        env = ModuleEnvironment.objects.filter(engine_app_id=bp.app_id).first()
        if env:
            return env.environment
        return None

    def get_image_tag(self, bp: BuildProcess):
        if not bp.build:
            return None
        return bp.build.image_tag


class GetReleasedInfoSLZ(serializers.Serializer):
    with_processes = serializers.BooleanField(default=False)


class CreateOfflineOperationSLZ(serializers.Serializer):
    pass


class OfflineOperationSLZ(serializers.ModelSerializer):
    operator = UserField(read_only=True)

    class Meta:
        model = OfflineOperation
        fields = ["id", "status", "operator", "created", "log", "err_detail"]

    def get_repo_info(self, obj: OfflineOperation) -> dict:
        """Get deployment's repo info as dict"""
        version_info = obj.get_version_info()
        revision = version_info.revision
        version_type = version_info.version_type
        version_name = version_info.version_name

        return {
            "source_type": obj.source_type,
            "type": version_type,
            "name": version_name,
            "url": obj.source_location,
            "revision": revision,
            "comment": obj.source_comment,
        }

    def to_representation(self, obj):
        """Format a obj to presentation"""
        result = super(OfflineOperationSLZ, self).to_representation(obj)
        result.update(
            offline_operation_id=obj.id, environment=obj.app_environment.environment, repo=self.get_repo_info(obj)
        )
        return result


class OperationSLZ(serializers.ModelSerializer):
    """This serializer is only for presentation purpose"""

    operator = UserField(read_only=True)
    offline_operation = OfflineOperationSLZ(source="get_offline_obj")
    deployment = DeploymentSLZ(source="get_deployment_obj")
    module_name = SerializerMethodField()

    class Meta:
        model = ModuleEnvironmentOperations
        fields = [
            "id",
            "status",
            "operator",
            "created",
            "operation_type",
            "offline_operation",
            "deployment",
            "module_name",
        ]

    def get_module_name(self, obj: ModuleEnvironmentOperations) -> str:
        return obj.app_environment.module.name


#################
# env variables #
#################
class PresetEnvVarSLZ(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.CharField()
    environment_name = serializers.CharField()
    description = serializers.CharField(default="")


class EnvironmentSlugFieldSupportGlobal(serializers.RelatedField):
    queryset = ModuleEnvironment.objects.all()
    default_error_messages = {
        "does_not_exist": _("Object with {slug_name}={value} does not exist."),
        "invalid": _("Invalid value."),
    }

    def get_choices(self, cutoff=None):
        return ConfigVarEnvName.get_choices()

    def get_attribute(self, instance):
        # 实际上全局环境变量并未绑定到 environment, 因此 super().get_attribute(instance) 会返回 None. 这里将其替换成 ENVIRONMENT_NAME_FOR_GLOBAL
        return super().get_attribute(instance) or ENVIRONMENT_NAME_FOR_GLOBAL

    def to_representation(self, value: ModuleEnvironment):
        if isinstance(value, ModuleEnvironment):
            value = value.environment
        return ConfigVarEnvName(value).value

    def to_internal_value(self, name: str):
        # 约定使用 -1 代表全局环境变量, 因此返回 None
        if name == ENVIRONMENT_NAME_FOR_GLOBAL:
            return None

        try:
            return self.queryset.get(environment=name, module=self.context["module"])
        except ModuleEnvironment.DoesNotExist:
            self.fail("does_not_exist", slug_name="environment", value=str(name))
        except (TypeError, ValueError):
            self.fail("invalid")


class ConfigVarUniqueTogetherValidator(UniqueTogetherValidator):
    def __call__(self, attrs, serializer):
        # 实现复制自 UniqueTogetherValidator, 但是将报错信息转为更可读的文案。
        self.enforce_required_fields(attrs, serializer)
        queryset = self.queryset
        queryset = self.filter_queryset(attrs, queryset, serializer)
        queryset = self.exclude_current_instance(attrs, queryset, serializer.instance)

        # Ignore validation if any field is None
        checked_values = [value for field, value in attrs.items() if field in self.fields]
        if None not in checked_values and qs_exists(queryset):
            if serializer.instance is not None:
                message = _("该环境下同名变量 {key} 已存在。").format(key=attrs["key"])
            else:
                message = _("该环境下名称为 {key} 的变量已经存在，不能重复添加。").format(key=attrs["key"])
            raise ValidationError(message, code="unique")


class ConfigVarSLZ(serializers.ModelSerializer):
    environment_name = EnvironmentSlugFieldSupportGlobal(
        allow_null=True,
        required=True,
        source="environment",
    )
    key = field_env_var_key()
    value = serializers.CharField(required=True, help_text="环境变量值")
    is_sensitive = serializers.BooleanField(required=False, default=False, help_text="变量值是否敏感")
    description = serializers.CharField(
        allow_blank=True, max_length=200, required=False, default="", help_text="变量描述，不超过 200 个字符"
    )
    is_global = serializers.BooleanField(required=False, help_text="是否全局有效, 该字段由 slz 补充.")
    # 只读字段, 仅序列化时 ConfigVar 对象时生效
    id = serializers.IntegerField(read_only=True)
    is_builtin = serializers.BooleanField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    # 只写字段, 仅参与 UniqueTogetherValidator 的校验. 对于 global 类型的环境变量, environment=None, 因此不能使用 environment 作为唯一约束.
    environment_id = serializers.IntegerField(write_only=True, help_text="该字段由 slz 补充.")

    class Meta:
        model = ConfigVar
        validators = [
            ConfigVarUniqueTogetherValidator(
                queryset=ConfigVar.objects.all(),
                fields=("module", "is_global", "environment_id", "key"),
            )
        ]
        exclude = ("region", "environment")

    def to_internal_value(self, data):
        """Do following things:

        - Query for environment_id for validator.
        - Add Module field from context.
        """
        module = self.context.get("module")
        env_name = data["environment_name"]
        if env_name == ENVIRONMENT_NAME_FOR_GLOBAL:
            data["is_global"] = True
            data["environment_id"] = ENVIRONMENT_ID_FOR_GLOBAL
        else:
            data["is_global"] = False
            data["environment_id"] = module.get_envs(env_name).pk
        data["module"] = module.pk
        data["tenant_id"] = module.tenant_id
        return super().to_internal_value(data)

    def to_representation(self, instance) -> dict:
        ret = super().to_representation(instance)
        if ret.get("is_sensitive"):
            ret["value"] = MASKED_CONTENT
        return ret


class CreateConfigVarInputSLZ(ConfigVarSLZ):
    """Serializer for creating ConfigVars"""


class UpdateConfigVarInputSLZ(ConfigVarSLZ):
    """Serializer for updating ConfigVars"""

    value = serializers.CharField(required=False, help_text="环境变量值")
    is_sensitive = serializers.BooleanField(read_only=True)


class ListConfigVarsQuerySLZ(serializers.Serializer):
    """Query Serializer for listing ConfigVars"""

    valid_order_by_fields = {"created", "key"}

    environment_name = serializers.ChoiceField(
        choices=ConfigVarEnvName.get_choices(), required=False, help_text="按生效环境过滤"
    )
    order_by = serializers.CharField(default="-created", help_text='排序方式，可选："-created", "key"')

    def validate_environment_name(self, value: str) -> ConfigVarEnvName:
        return ConfigVarEnvName(value)

    def validate_order_by(self, field: str) -> str:
        f = OrderByField.from_string(field)
        if f.name not in self.valid_order_by_fields:
            raise ValidationError(_("无效的排序选项：%s") % f)
        return field


class ConfigVarBaseSLZ(serializers.Serializer):
    """ConfigVar 基础 SLZ"""

    value = serializers.CharField(required=False, help_text="环境变量值")
    is_sensitive = serializers.BooleanField(required=False, default=False, help_text="变量值是否敏感")
    environment_name = serializers.ChoiceField(choices=ConfigVarEnvName.get_choices(), required=True)
    description = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        max_length=200,
        required=False,
        default="",
        help_text="变量描述，不超过 200 个字符",
    )

    def to_internal_value(self, data):
        """Do following things:

        - Query for environment_id
        - bind module from context
        - return a non-persistent ConfigVar
        """
        data = super().to_internal_value(data)
        module = self.context.get("module")
        env_name = data.pop("environment_name")
        if env_name == ENVIRONMENT_NAME_FOR_GLOBAL:
            data["is_global"] = True
            data["environment_id"] = ENVIRONMENT_ID_FOR_GLOBAL
        else:
            data["is_global"] = False
            data["environment_id"] = module.envs.get(environment=env_name).pk
        return ConfigVar(**data, module=module, tenant_id=module.tenant_id)


class ConfigVarBaseInputSLZ(ConfigVarBaseSLZ):
    """ConfigVar 基础输入 SLZ"""

    key = field_env_var_key()


class ConfigVarUpsertByKeyInputSLZ(ConfigVarBaseSLZ):
    """通过 key 更新或创建 ConfigVar 的输入 SLZ"""


class ConfigVarOperateAuditOutputSLZ(ConfigVarBaseInputSLZ):
    """ConfigVar 审计输出 SLZ, 敏感值会被 masked"""

    def to_representation(self, instance) -> dict:
        ret = super().to_representation(instance)
        if ret.get("is_sensitive"):
            ret["value"] = MASKED_CONTENT
        return ret


class ConfigVarApplyResultSLZ(serializers.Serializer):
    """Serializer for ConfigVar ApplyResult"""

    create_num = serializers.IntegerField()
    overwrited_num = serializers.IntegerField()
    ignore_num = serializers.IntegerField()
    deleted_num = serializers.IntegerField()


class ConfigVarBatchInputSLZ(ConfigVarBaseInputSLZ):
    """批量编辑 ConfigVar 输入 SLZ, 更新需传入 id, 新建不必传入 id"""

    id = serializers.IntegerField(required=False)


class ConfigVarImportItemSLZ(ConfigVarBaseInputSLZ):
    """从文件中导入 ConfigVar 的 SLZ, 必须传入 value"""

    value = serializers.CharField(required=True, help_text="环境变量值")


class ConfigVarImportSLZ(serializers.Serializer):
    """Serializer for ConfigVarImport"""

    file = serializers.FileField(required=True, help_text="Only yaml format files are accepted")
    env_variables = ConfigVarImportItemSLZ(required=False, many=True, help_text="Only yaml format files are accepted")

    def to_internal_value(self, data):
        # 从 request 获取的 data 属于 MultiValueDict, 在解析数组时会有奇怪的逻辑, 这里将 data 转换成原生的 dict 类型, 避免意外情况。
        # see also: rest_framework.utils.html::parse_html_list
        data = dict(data.items())
        try:
            content = yaml.safe_load(data["file"])
        except yaml.YAMLError:
            raise error_codes.NOT_YAML_FILE
        if "env_variables" not in content:
            raise error_codes.ERROR_FILE_FORMAT
        data["env_variables"] = content["env_variables"]
        return super().to_internal_value(data)


#####################
# resources metrics #
#####################
class ResourceMetricsSLZ(serializers.Serializer):
    process_type = serializers.CharField()
    metric_type = serializers.ChoiceField(MetricsType.get_choices(), required=False)
    start_time = serializers.CharField(required=False)
    end_time = serializers.CharField(required=False)
    instance_name = serializers.CharField(required=False)
    time_range_str = serializers.CharField(required=False)

    step = serializers.SerializerMethodField()
    query_metrics = serializers.SerializerMethodField()

    def validate(self, attrs):
        if attrs.get("time_range_str"):
            return attrs

        if not (attrs.get("start_time") and attrs.get("end_time")):
            raise serializers.ValidationError("start & end not allowed to be null if no time_range_str pass in")

        start_time = datetime.fromisoformat(attrs["start_time"])
        end_time = datetime.fromisoformat(attrs["end_time"])

        if start_time > end_time:
            raise serializers.ValidationError("start time should earlier than end time")

        return attrs

    def get_step(self, attrs) -> str:
        # default min interval of metrics is 15s, get step automatically instead of choosing by user
        if attrs.get("time_range_str"):
            return calculate_gap_seconds_interval(get_time_delta(attrs.get("time_range_str")).total_seconds())

        time_delta = datetime.fromisoformat(attrs.get("end_time")) - datetime.fromisoformat(attrs.get("start_time"))
        return calculate_gap_seconds_interval(time_delta.total_seconds())

    def get_query_metrics(self, attrs):
        """根据 metric_type 注入 query_metrics 字段"""
        if "metric_type" in attrs and attrs["metric_type"] != "__all__":
            return [MetricsResourceType(attrs["metric_type"]).value]

        return [MetricsResourceType.MEM.value, MetricsResourceType.CPU.value]


class SeriesMetricsResultSerializer(serializers.Serializer):
    type_name = serializers.CharField()
    results = serializers.ListField()
    display_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["display_name"] = MetricsSeriesType.get_choice_label(instance.type_name)
        return result


class ResourceMetricsResultSerializer(serializers.Serializer):
    type_name = serializers.CharField()
    results = SeriesMetricsResultSerializer(allow_null=True, many=True)


class InstanceMetricsResultSerializer(serializers.Serializer):
    instance_name = serializers.CharField()
    results = ResourceMetricsResultSerializer(allow_null=True, many=True)
    display_name = serializers.CharField(required=False)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["display_name"] = Instance.get_shorter_instance_name(instance.instance_name)
        return result


class CustomDomainsConfigSLZ(serializers.Serializer):
    module = serializers.CharField(help_text="所属模块")
    environment = serializers.CharField(help_text="部署环境")
    frontend_ingress_ip = serializers.CharField(
        help_text='独立域名应该指向的地址，为空字符串 "" 时表示不支持独立域名功能'
    )


class ConditionNotMatchedSLZ(serializers.Serializer):
    message = serializers.CharField()
    action_name = serializers.ChoiceField(choices=DeployConditions.get_choices())


class CheckPreparationsSLZ(serializers.Serializer):
    all_conditions_matched = serializers.BooleanField()
    failed_conditions = serializers.ListField(child=ConditionNotMatchedSLZ())
    replicas_manually_scaled = serializers.BooleanField(help_text="是否通过页面手动扩缩容过")


#########################
# DeployPhase Responses #
#########################
class EngineAppSLZ(serializers.Serializer):
    name = serializers.CharField()
    id = serializers.CharField()


class DeployStepFrameSLZ(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.SerializerMethodField()
    skipped = serializers.BooleanField()

    def get_display_name(self, obj) -> str:
        return obj.display_name or obj.name


class DeployStepSLZ(DeployStepFrameSLZ):
    """Step with 执行结果"""

    uuid = serializers.CharField()
    status = serializers.ChoiceField(choices=JobStatus.get_choices(), required=False)
    start_time = serializers.DateTimeField(required=False)
    complete_time = serializers.DateTimeField(required=False)

    class Meta:
        # Set a ref_name to avoid conflicts for drf-yasg
        ref_name = "PluginDeployStepSLZ__engine"


class DeployFramePhaseSLZ(serializers.Serializer):
    display_name = serializers.SerializerMethodField()
    type = serializers.ChoiceField(choices=DeployPhaseTypes.get_choices())
    steps = DeployStepFrameSLZ(source="_sorted_steps", many=True)
    display_blocks = serializers.SerializerMethodField()

    def get_display_name(self, obj) -> str:
        return DeployPhaseTypes.get_choice_label(obj.type)

    def get_display_blocks(self, obj) -> dict:
        return DeployDisplayBlockRenderer.get_display_blocks_info(obj)


class DeployPhaseSLZ(DeployFramePhaseSLZ):
    """Phase with 执行结果"""

    uuid = serializers.CharField()
    status = serializers.ChoiceField(choices=JobStatus.get_choices(), required=False)
    start_time = serializers.DateTimeField(required=False)
    complete_time = serializers.DateTimeField(required=False)
    steps = DeployStepSLZ(source="_sorted_steps", many=True)


class ImageArtifactMinimalSLZ(serializers.Serializer):
    """镜像构件概览"""

    id = serializers.CharField(help_text="构件ID", source="uuid")
    repository = serializers.CharField(help_text="镜像仓库", source="image_repository")
    tag = serializers.CharField(help_text="镜像 Tag", source="image_tag")
    size = serializers.IntegerField(help_text="镜像大小", source="get_artifact_detail.size")
    digest = serializers.CharField(help_text="摘要", source="get_artifact_detail.digest")
    invoke_message = serializers.CharField(help_text="触发信息", source="artifact_invoke_message")
    updated = serializers.DateTimeField(help_text="更新时间")

    operator = serializers.SerializerMethodField(help_text="操作人")

    def get_operator(self, build: Build) -> str:
        try:
            return get_username_by_bkpaas_user_id(build.owner)
        except ValueError:
            return build.owner


class ImageDeployRecord(serializers.Serializer):
    """镜像部署记录"""

    at = serializers.DateTimeField(help_text="部署成功时间")
    operator = serializers.SerializerMethodField(help_text="操作人")
    environment = serializers.CharField(help_text="部署环境")

    def get_operator(self, record) -> str:
        try:
            return get_username_by_bkpaas_user_id(record["operator"])
        except ValueError:
            return record["operator"]


class ImageArtifactDetailSLZ(serializers.Serializer):
    """镜像构件详情"""

    image_info = ImageArtifactMinimalSLZ(help_text="镜像详情")
    build_records = ImageArtifactMinimalSLZ(many=True, default=list, help_text="构建记录")
    deploy_records = ImageDeployRecord(many=True, default=list, help_text="部署记录")


class ModuleEnvOverviewSLZ(serializers.Serializer):
    is_deployed = serializers.BooleanField(help_text="是否已部署")
    address = AvailableAddressSLZ(allow_null=True, help_text="平台提供的访问地址")
    build_method = serializers.ChoiceField(help_text="构建方式", choices=RuntimeType.get_choices(), required=True)
    # 版本相关信息
    version_type = serializers.CharField(required=True, help_text="版本类型, 如 branch/tag/trunk")
    version_name = serializers.CharField(
        required=True, help_text="版本名称: 如 Tag Name/Branch Name/trunk/package_name"
    )
    revision = serializers.CharField(
        required=False,
        help_text="版本信息, 如 hash(git版本)/version(源码包); 如果根据 smart_revision 能查询到 revision, 则不使用该值",
    )

    # 进程相关信息
    process_specs = ProcessSpecSLZ(many=True, help_text="进程规格")


class EnvOverviewSLZ(serializers.Serializer):
    """环境概览视图"""

    environment = serializers.CharField(help_text="部署环境")
    modules = ModuleEnvOverviewSLZ(many=True)


class BuiltinConfigVarSLZ(serializers.Serializer):
    """Serializer for Builtin ConfigVar"""

    key = serializers.CharField(help_text="内置环境变量 key")
    value = serializers.CharField(help_text="内置环境变量值")
    description = serializers.CharField(help_text="内置环境变量描述")
    is_sensitive = serializers.BooleanField(default=False, help_text="是否为敏感字段")


class ListBuiltinConfigVarSLZ(serializers.Serializer):
    stag = BuiltinConfigVarSLZ(many=True, help_text="预发布环境下的内置环境变量")
    prod = BuiltinConfigVarSLZ(many=True, help_text="生产环境下的内置环境变量")


class ConflictedEnvVarInfoOutputSLZ(serializers.Serializer):
    """Serializer for represent ConflictedEnvVarInfo"""

    key = serializers.CharField(help_text="有冲突的环境变量 Key")
    conflicted_source = serializers.CharField(help_text="冲突来源，比如 builtin_addons, builtin_svc_disc 等")
    conflicted_detail = serializers.CharField(
        help_text="冲突详情，通常为该环境变量的详细描述，比如 builtin_addons 来源的该字段为增强服务名称"
    )
    override_conflicted = serializers.BooleanField(help_text="冲突发生后，用户定义的 Key 是否生效")


class DeployOptionsSLZ(serializers.Serializer):
    replicas_policy = serializers.ChoiceField(choices=ReplicasPolicy.get_choices(), help_text="副本数的优先策略")
